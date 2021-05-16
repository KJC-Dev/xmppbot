#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Slixmpp OMEMO plugin
    Copyright (C) 2019 Maxime “pep” Buquet <pep@bouah.net>
    This file is part of slixmpp-omemo.

    See the file LICENSE for copying permission.
"""

import logging

from typing import Any, Dict, List, Optional, Set, Tuple, Union

import os
import json
import base64
import codecs
import asyncio
from slixmpp.plugins.xep_0060.stanza import Items, EventItems
from slixmpp.plugins.xep_0004 import Form
from slixmpp.plugins.base import BasePlugin, register_plugin
from slixmpp.exceptions import IqError, IqTimeout
from slixmpp.stanza import Message, Iq
from slixmpp.jid import JID

from .version import __version__, __version_info__
from .stanza import OMEMO_BASE_NS
from .stanza import OMEMO_DEVICES_NS, OMEMO_BUNDLES_NS
from .stanza import Bundle, Devices, Device, Encrypted, Key, PreKeyPublic

log = logging.getLogger(__name__)

HAS_OMEMO = False
HAS_OMEMO_BACKEND = False
try:
    import omemo.exceptions
    from omemo import SessionManager, ExtendedPublicBundle, DefaultOTPKPolicy
    from omemo.util import generateDeviceID
    from omemo.implementations import JSONFileStorage
    from omemo.backends import Backend
    HAS_OMEMO = True
    from omemo_backend_signal import BACKEND as SignalBackend
    HAS_OMEMO_BACKEND = True
except (ImportError,):
    class Backend:
        pass

    class DefaultOTPKPolicy:
        pass

    class SignalBackend:
        pass

TRUE_VALUES = {True, 'true', '1'}
PUBLISH_OPTIONS_NODE = 'http://jabber.org/protocol/pubsub#publish-options'
PUBSUB_ERRORS = 'http://jabber.org/protocol/pubsub#errors'


def b64enc(data: bytes) -> str:
    return base64.b64encode(bytes(bytearray(data))).decode('ASCII')


def b64dec(data: str) -> bytes:
    return base64.b64decode(data)


def _load_device_id(data_dir: str) -> int:
    filepath = os.path.join(data_dir, 'device_id.json')
    # Try reading file first, decoding, and if file was empty generate
    # new DeviceID
    try:
        with open(filepath, 'r') as f:
            did = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        did = generateDeviceID()
        with open(filepath, 'w') as f:
            json.dump(did, f)

    return did


def fp_from_ik(identity_key: bytes) -> str:
    """Convert identityKey to a string representation (fingerprint)"""
    return codecs.getencoder("hex")(identity_key)[0].decode("US-ASCII").upper()


def _parse_bundle(backend: Backend, bundle: Bundle) -> ExtendedPublicBundle:
    identity_key = b64dec(bundle['identityKey']['value'].strip())
    spk = {
        'id': int(bundle['signedPreKeyPublic']['signedPreKeyId']),
        'key': b64dec(bundle['signedPreKeyPublic']['value'].strip()),
    }
    spk_signature = b64dec(bundle['signedPreKeySignature']['value'].strip())

    otpks = []
    for prekey in bundle['prekeys']:
        otpks.append({
            'id': int(prekey['preKeyId']),
            'key': b64dec(prekey['value'].strip()),
        })

    return ExtendedPublicBundle.parse(backend, identity_key, spk, spk_signature, otpks)


def _generate_encrypted_payload(encrypted) -> Encrypted:
    tag = Encrypted()

    tag['header']['sid'] = str(encrypted['sid'])
    tag['header']['iv']['value'] = b64enc(encrypted['iv'])
    tag['payload']['value'] = b64enc(encrypted['payload'])

    for bare_jid, devices in encrypted['keys'].items():
        for rid, device in devices.items():
            key = Key()
            key['value'] = b64enc(device['data'])
            key['rid'] = str(rid)
            if device['pre_key']:
                key['prekey'] = '1'
            tag['header'].append(key)

    return tag


def _make_publish_options_form(fields: Dict[str, Any]) -> Form:
    options = Form()
    options['type'] = 'submit'
    options.add_field(
        var='FORM_TYPE',
        ftype='hidden',
        value='http://jabber.org/protocol/pubsub#publish-options',
    )

    for var, value in fields.items():
        options.add_field(var=var, value=value)

    return options


# XXX: This should probably be moved in plugins/base.py?
class PluginCouldNotLoad(Exception): pass


# Generic exception
class XEP0384(Exception): pass


class MissingOwnKey(XEP0384): pass


class NoAvailableSession(XEP0384): pass


class EncryptionPrepareException(XEP0384):
    def __init__(self, errors):
        self.errors = errors


class UntrustedException(XEP0384):
    def __init__(self, bare_jid, device, ik):
        self.bare_jid = JID(bare_jid)
        self.device = device
        self.ik = ik


class UndecidedException(XEP0384):
    def __init__(self, bare_jid, device, ik):
        self.bare_jid = JID(bare_jid)
        self.device = device
        self.ik = ik


class XEP_0384(BasePlugin):

    """
    XEP-0384: OMEMO
    """

    name = 'xep_0384'
    description = 'XEP-0384 OMEMO'
    dependencies = {'xep_0004', 'xep_0060', 'xep_0163'}
    default_config = {
        'data_dir': None,
        'storage_backend': None,
        'otpk_policy': DefaultOTPKPolicy,
        'omemo_backend': SignalBackend,
    }

    backend_loaded = HAS_OMEMO and HAS_OMEMO_BACKEND

    # OMEMO Bundles used for encryption
    bundles = {}  # type: Dict[str, Dict[int, ExtendedPublicBundle]]

    def plugin_init(self) -> None:
        if not self.backend_loaded:
            log_str = ("xep_0384 cannot be loaded as the backend omemo library "
                       "is not available. ")
            if not HAS_OMEMO_BACKEND:
                log_str += ("Make sure you have a python OMEMO backend "
                            "(python-omemo-backend-signal) installed")
            else:
                log_str += "Make sure you have the python OMEMO library installed."
            log.error(log_str)
            raise PluginCouldNotLoad

        if not self.data_dir:
            log.info("xep_0384 cannot be loaded as there is not data directory "
                     "specified")
            return None

        storage = self.storage_backend
        if self.storage_backend is None:
            storage = JSONFileStorage(self.data_dir)

        otpkpolicy = self.otpk_policy
        bare_jid = self.xmpp.boundjid.bare
        self._device_id = _load_device_id(self.data_dir)

        try:
            self._omemo = SessionManager.create(
                storage,
                otpkpolicy,
                self.omemo_backend,
                bare_jid,
                self._device_id,
            )
        except:
            log.error("Couldn't load the OMEMO object; ¯\\_(ツ)_/¯")
            raise PluginCouldNotLoad

        self.xmpp.add_event_handler('session_start', self.session_start)
        self.xmpp['xep_0060'].map_node_event(OMEMO_DEVICES_NS, 'omemo_device_list')
        self.xmpp.add_event_handler('omemo_device_list_publish', self._receive_device_list)
        return None

    def plugin_end(self):
        if not self.backend_loaded:
            return

        self.xmpp.remove_event_handler('session_start', self.session_start)
        self.xmpp.remove_event_handler('omemo_device_list_publish', self._receive_device_list)
        self.xmpp['xep_0163'].remove_interest(OMEMO_DEVICES_NS)

    async def session_start(self, _jid):
        if self.backend_loaded:
            self.xmpp['xep_0163'].add_interest(OMEMO_DEVICES_NS)
            await asyncio.wait([
                self._set_device_list(),
                self._publish_bundle(),
            ])

    def my_device_id(self) -> int:
        return self._device_id

    def _set_node_config(
            self,
            node: str,
            persist_items: bool = True,
            access_model: Optional[str] = None,
        ) -> asyncio.Future:
        """
            Sets OMEMO devicelist or bundle node configuration.

            This function is meant to be used once we've tried publish options
            and they came back with precondition-not-met. This means an
            existing node is not using our defaults.

            By default this function will be overwriting pubsub#persist_items
            only, leaving pubsub#access_model as it was.

            To be complete, the code using this function should probably
            set the bundle node to the same access_model as the devicelist
            node.
        """
        form = Form()
        form['type'] = 'submit'
        form.add_field(
            var='FORM_TYPE',
            ftype='hidden',
            value='http://jabber.org/protocol/pubsub#node_config',
        )
        if persist_items:
            form.add_field(
                var='pubsub#persist_items',
                ftype='boolean',
                value=True,
            )
        if access_model is not None:
            form.add_field(
                var='FORM_TYPE',
                ftype='text-single',
                value=access_model,
            )

        return self.xmpp['xep_0060'].set_node_config(
            self.xmpp.boundjid.bare,
            node,
            form,
        )

    async def _generate_bundle_iq(self, publish_options: bool = True) -> Iq:
        bundle = self._omemo.public_bundle.serialize(self.omemo_backend)

        jid = self.xmpp.boundjid
        disco = await self.xmpp['xep_0030'].get_info(jid.bare)
        publish_options = PUBLISH_OPTIONS_NODE in disco['disco_info'].get_features()

        iq = self.xmpp.Iq(stype='set')

        publish = iq['pubsub']['publish']
        publish['node'] = '%s:%d' % (OMEMO_BUNDLES_NS, self._device_id)
        payload = publish['item']['bundle']
        signedPreKeyPublic = b64enc(bundle['spk']['key'])
        payload['signedPreKeyPublic']['value'] = signedPreKeyPublic
        payload['signedPreKeyPublic']['signedPreKeyId'] = str(bundle['spk']['id'])
        payload['signedPreKeySignature']['value'] = b64enc(
            bundle['spk_signature']
        )
        identityKey = b64enc(bundle['ik'])
        payload['identityKey']['value'] = identityKey

        prekeys = []
        for otpk in bundle['otpks']:
            prekey = PreKeyPublic()
            prekey['preKeyId'] = str(otpk['id'])
            prekey['value'] = b64enc(otpk['key'])
            prekeys.append(prekey)
        payload['prekeys'] = prekeys

        if publish_options and publish_options:
            options = _make_publish_options_form({
                'pubsub#persist_items': True,
                'pubsub#access_model': 'open',
            })
            iq['pubsub']['publish_options'] = options

        return iq

    async def _publish_bundle(self) -> None:
        if self._omemo.republish_bundle:
            iq = await self._generate_bundle_iq()
            try:
                await iq.send()
            except IqError as e:
                # TODO: Slixmpp should handle pubsub#errors so we don't have to
                # fish the element ourselves
                precondition = e.iq['error'].xml.find(
                    '{%s}%s' % (PUBSUB_ERRORS, 'precondition-not-met'),
                )
                if precondition is not None:
                    log.debug('The node we tried to publish was already '
                              'existing with a different configuration. '
                              'Trying to configure manually..')
                    # TODO: We should attempt setting this node to the same
                    # access_model as the devicelist node for completness.
                    try:
                        await self._set_node_config(OMEMO_BUNDLES_NS)
                    except IqError:
                        log.debug('Failed to set node to persistent after precondition-not-met')
                        raise
                    iq = await self._generate_bundle_iq(publish_options=False)
                    await iq.send()

    async def _fetch_bundle(self, jid: str, device_id: int) -> Optional[ExtendedPublicBundle]:
        node = '%s:%d' % (OMEMO_BUNDLES_NS, device_id)
        try:
            iq = await self.xmpp['xep_0060'].get_items(jid, node)
        except (IqError, IqTimeout):
            return None
        bundle = iq['pubsub']['items']['item']['bundle']

        return _parse_bundle(self.omemo_backend, bundle)

    async def _fetch_device_list(self, jid: JID) -> None:
        """Manually query PEP OMEMO_DEVICES_NS nodes"""
        iq = await self.xmpp['xep_0060'].get_items(jid.full, OMEMO_DEVICES_NS)
        return await self._read_device_list(jid, iq['pubsub']['items'])

    def _store_device_ids(self, jid: str, items: Union[Items, EventItems]) -> None:
        """Store Device list"""
        device_ids = []  # type: List[int]
        items = list(items)
        if items:
            device_ids = [int(d['id']) for d in items[0]['devices']]
        return self._omemo.newDeviceList(str(jid), device_ids)

    def _receive_device_list(self, msg: Message) -> None:
        """Handler for received PEP OMEMO_DEVICES_NS payloads"""
        asyncio.ensure_future(
            self._read_device_list(msg['from'], msg['pubsub_event']['items']),
        )

    async def _read_device_list(self, jid: JID, items: Union[Items, EventItems]) -> None:
        """Read items and devices if we need to set the device list again or not"""
        bare_jid = jid.bare
        self._store_device_ids(bare_jid, items)

        items = list(items)
        device_ids = []
        if items:
            device_ids = [int(d['id']) for d in items[0]['devices']]

        if bare_jid == self.xmpp.boundjid.bare and \
           self._device_id not in device_ids:
            await self._set_device_list()

        return None

    async def _set_device_list(self, device_ids: Optional[Set[int]] = None) -> None:
        own_jid = self.xmpp.boundjid

        try:
            iq = await self.xmpp['xep_0060'].get_items(
                own_jid.bare, OMEMO_DEVICES_NS,
            )
            items = iq['pubsub']['items']
            self._store_device_ids(own_jid.bare, items)
        except IqError as iq_err:
            if iq_err.condition == "item-not-found":
                self._store_device_ids(own_jid.bare, [])
            else:
                return  # XXX: Handle this!

        if device_ids is None:
            device_ids = self.get_device_list(own_jid)

        devices = []
        for i in device_ids:
            d = Device()
            d['id'] = str(i)
            devices.append(d)
        payload = Devices()
        payload['devices'] = devices

        jid = self.xmpp.boundjid
        disco = await self.xmpp['xep_0030'].get_info(jid.bare)
        publish_options = PUBLISH_OPTIONS_NODE in disco['disco_info'].get_features()

        options = None
        if publish_options:
            options = _make_publish_options_form({
                'pubsub#persist_items': True,
                # Everybody will be able to encrypt for us, without having to add
                # us into their roster. This obviously leaks the number of devices
                # and the associated metadata of us pushing new device lists every
                # so often.
                'pubsub#access_model': 'open',
            })

        try:
            await self.xmpp['xep_0060'].publish(
                own_jid.bare, OMEMO_DEVICES_NS, payload=payload, options=options,
            )
        except IqError as e:
            # TODO: Slixmpp should handle pubsub#errors so we don't have to
            # fish the element ourselves
            precondition = e.iq['error'].xml.find(
                '{%s}%s' % (PUBSUB_ERRORS, 'precondition-not-met'),
            )
            if precondition is not None:
                log.debug('The node we tried to publish was already '
                          'existing with a different configuration. '
                          'Trying to configure manually..')
                try:
                    await self._set_node_config(OMEMO_DEVICES_NS)
                except IqError:
                    log.debug('Failed to set node to persistent after precondition-not-met')
                    raise
                await self.xmpp['xep_0060'].publish(
                    own_jid.bare, OMEMO_DEVICES_NS, payload=payload,
                )

    def get_device_list(self, jid: JID) -> List[str]:
        """Return active device ids. Always contains our own device id."""
        return self._omemo.getDevices(jid.bare).get('active', [])

    def trust(self, jid: JID, device_id: int, ik: bytes) -> None:
        self._omemo.setTrust(jid.bare, device_id, ik, True)

    def distrust(self, jid: JID, device_id: int, ik: bytes) -> None:
        self._omemo.setTrust(jid.bare, device_id, ik, False)

    def get_trust_for_jid(self, jid: JID) -> Dict[str, List[Optional[Dict[str, Any]]]]:
        """
            Fetches trust for JID. The returned dictionary will contain active
            and inactive devices. Each of these dict will contain device ids
            as keys, and a dict with 'key', 'trust' as values that can also be
            None.

            Example:
            {
                'active': {
                    123456: {
                        'key': bytes,
                        'trust': bool,
                    }
                }
                'inactive': {
                    234567: None,
                }
            }
        """

        return self._omemo.getTrustForJID(jid.bare)

    def is_encrypted(self, msg: Message) -> bool:
        return msg.xml.find('{%s}encrypted' % OMEMO_BASE_NS) is not None

    def decrypt_message(
        self,
        encrypted: Encrypted,
        sender: JID,
        allow_untrusted: bool = False,
    ) -> Optional[str]:
        header = encrypted['header']
        payload = b64dec(encrypted['payload']['value'])

        jid = sender.bare
        sid = int(header['sid'])

        key = header.xml.find("{%s}key[@rid='%s']" % (
            OMEMO_BASE_NS, self._device_id))
        if key is None:
            raise MissingOwnKey("Encrypted message is not for us")

        key = Key(key)
        isPrekeyMessage = key['prekey'] in TRUE_VALUES
        message = b64dec(key['value'])
        iv = b64dec(header['iv']['value'])

        # XXX: 'cipher' is part of KeyTransportMessages and is used when no payload
        # is passed. We do not implement this yet.
        try:
            body = self._omemo.decryptMessage(
                jid,
                sid,
                iv,
                message,
                isPrekeyMessage,
                payload,
                allow_untrusted=allow_untrusted,
            )
            return body
        except (omemo.exceptions.NoSessionException,):
            # This might happen when the sender is sending using a session
            # that we don't know about (deleted session storage, etc.). In
            # this case we can't decrypt the message and it's going to be lost
            # in any case, but we want to tell the user, always.
            raise NoAvailableSession(jid, sid)
        except (omemo.exceptions.TrustException,) as exn:
            if exn.problem == 'undecided':
                raise UndecidedException(exn.bare_jid, exn.device, exn.ik)
            if exn.problem == 'untrusted':
                raise UntrustedException(exn.bare_jid, exn.device, exn.ik)
            raise
        finally:
            asyncio.ensure_future(self._publish_bundle())

    async def encrypt_message(
        self,
        plaintext: str,
        recipients: List[JID],
        expect_problems: Optional[Dict[JID, List[int]]] = None,
    ) -> Encrypted:
        """
        Returns an encrypted payload to be placed into a message.

        The API for getting an encrypted payload consists of trying first
        and fixing errors progressively. The actual sending happens once the
        application (us) thinks we're good to go.
        """

        recipients = [jid.bare for jid in recipients]

        old_errors = None  # type: Optional[List[Tuple[Exception, Any, Any]]]
        while True:
            # Try to encrypt and resolve errors until there is no error at all
            # or if we hit the same set of errors.
            errors = []  # type: List[omemo.exceptions.OMEMOException]

            if expect_problems is not None:
                expect_problems = {jid.bare: did for (jid, did) in expect_problems.items()}

            try:
                encrypted = self._omemo.encryptMessage(
                    recipients,
                    plaintext.encode('utf-8'),
                    self.bundles,
                    expect_problems=expect_problems,
                )
                return _generate_encrypted_payload(encrypted)
            except omemo.exceptions.EncryptionProblemsException as exn:
                errors = exn.problems

            if errors == old_errors:
                raise EncryptionPrepareException(errors)

            old_errors = errors

            for exn in errors:
                if isinstance(exn, omemo.exceptions.NoDevicesException):
                    await self._fetch_device_list(JID(exn.bare_jid))
                elif isinstance(exn, omemo.exceptions.MissingBundleException):
                    bundle = await self._fetch_bundle(exn.bare_jid, exn.device)
                    if bundle is not None:
                        devices = self.bundles.setdefault(exn.bare_jid, {})
                        devices[exn.device] = bundle
                elif isinstance(exn, omemo.exceptions.TrustException):
                    # On TrustException, there are two possibilities.
                    # Either trust has not been explicitely set yet, and is
                    # 'undecided', or the device is explicitely not
                    # trusted. When undecided, we need to ask our user to make
                    # a choice. If untrusted, then we can safely tell the
                    # OMEMO lib to not encrypt to this device
                    if exn.problem == 'undecided':
                        raise UndecidedException(exn.bare_jid, exn.device, exn.ik)
                    distrusted_jid = JID(exn.bare_jid)
                    expect_problems.setdefault(distrusted_jid, []).append(exn.device)
                elif isinstance(exn, omemo.exceptions.NoEligibleDevicesException):
                    # This error is returned by the library to specify that
                    # encryption is not possible to any device of a user.
                    # This always comes with a more specific exception, (empty
                    # device list, missing bundles, trust issues, etc.).
                    # This does the heavy lifting of state management, and
                    # seeing if it's possible to encrypt at all, or not.
                    # This exception is only passed to the user, that should
                    # decide what to do with it, as there isn't much we can do if
                    # other issues can't be resolved.
                    continue


register_plugin(XEP_0384)
