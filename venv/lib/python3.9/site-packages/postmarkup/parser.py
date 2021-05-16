# -*- coding: UTF-8 -*-

__all__ = ["annotate_link",
           "textilize",
           "get_excerpt",
           "strip_bbcode",
           "escape",
           "TagBase",
           "SimpleTag",
           "DivStyleTag",
           "LinkTag",
           "QuoteTag",
           "SearchTag",
           "PygmentsCodeTag",
           "CodeTag",
           "ImgTag",
           "ListTag",
           "ListItemTag",
           "SizeTag",
           "ColorTag",
           "CenterTag",
           "SectionTag",
           "DefaultTag",
           "OrderedListTag",
           "create",
           "MultiReplace",
           "escape",
           "TagFactory",
           "PostMarkup",
           "render_bbcode"]

import re
from urllib.parse import quote_plus
from urllib.parse import urlparse
from collections import defaultdict

pygments_available = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, ClassNotFound
    from pygments.formatters import HtmlFormatter
except ImportError:
    # Make Pygments optional
    pygments_available = False


def annotate_link(domain):
    """This function is called by the url tag. Override to disable or change behaviour.

    domain -- Domain parsed from url

    """
    return " [%s]" % _escape(domain)


_re_url = re.compile(r"((https?):(//)+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE | re.UNICODE)
_re_html = re.compile(r'<.*?>|\&.*?\;', re.UNICODE | re.DOTALL)
_re_excerpt = re.compile(r'\[".*?\]+?.*?\[/".*?\]+?', re.DOTALL | re.UNICODE)
_re_remove_markup = re.compile(r'\[.*?\]', re.DOTALL | re.UNICODE)
_re_break_groups = re.compile('[\n]{2,}', re.DOTALL | re.UNICODE)


def textilize(s):
    """Remove markup from html"""
    s = s.replace("<p>", " ")
    return _re_html.sub("", s)


def get_excerpt(post):
    """Returns an excerpt between ["] and [/"]

    post -- BBCode string"""

    match = _re_excerpt.search(post)
    if match is None:
        return ""
    excerpt = match.group(0)
    excerpt = excerpt.replace('\n', "<br/>")
    return _re_remove_markup.sub("", excerpt)


def strip_bbcode(bbcode):
    """Strips bbcode tags from a string.

    bbcode -- A string to remove tags from

    """

    TOKEN_TEXT = PostMarkup.TOKEN_TEXT
    return "".join([t[1] for t in PostMarkup.tokenize(bbcode) if t[0] == TOKEN_TEXT])


class TagBase(object):

    def __init__(self, name, enclosed=False, auto_close=False, inline=False, strip_first_newline=False, **kwargs):
        """Base class for all tags.

        name -- The name of the bbcode tag
        enclosed -- True if the contents of the tag should not be bbcode processed.
        auto_close -- True if the tag is standalone and does not require a close tag.
        inline -- True if the tag generates an inline html tag.

        """
        self.name = name
        self.enclosed = enclosed
        self.auto_close = auto_close
        self.inline = inline
        self.strip_first_newline = strip_first_newline

        self.open_pos = None
        self.close_pos = None
        self.open_node_index = None
        self.close_node_index = None

    def open(self, parser, params, open_pos, node_index, tag_open_pos):
        """Called when the open tag is initially encountered."""
        self.params = params
        self.open_pos = open_pos
        self.open_node_index = node_index
        self.tag_open_pos = tag_open_pos

    def close(self, parser, close_pos, node_index):
        """Called when the close tag is initially encountered."""
        self.close_pos = close_pos
        self.close_node_index = node_index

    def render_open(self, parser, node_index):
        """Called to render the open tag."""
        pass

    def render_close(self, parser, node_index):
        """Called to render the close tag."""
        pass

    def get_contents(self, parser):
        """Returns the string between the open and close tag."""
        return parser.markup[self.open_pos:self.close_pos]

    def get_outer_contents(self, parser):
        return parser.markup[self.tag_open_pos:self.close_pos]

    def get_contents_text(self, parser):
        """Returns the string between the the open and close tag, minus bbcode tags."""
        return "".join(parser.get_text_nodes(self.open_node_index, self.close_node_index))

    def skip_contents(self, parser):
        """Skips the contents of a tag while rendering."""
        if self.close_node_index is not None:
            parser.skip_to_node(self.close_node_index)

    def __str__(self):
        return '[%s]' % self.name

    def __unicode__(self):
        return '[%s]' % self.name


class SimpleTag(TagBase):
    """A tag that can be rendered with a simple substitution. """

    def __init__(self, name, html_name, **kwargs):
        """html_name -- the html tag to substitute."""
        super(SimpleTag, self).__init__(name, inline=True)
        self.html_name = html_name

    def render_open(self, parser, node_index):
        tag_data = parser.tag_data
        tag_key = "SimpleTag.%s_nest_level" % self.html_name
        nest_level = tag_data[tag_key] = tag_data.setdefault(tag_key, 0) + 1

        if nest_level > 1:
            return ""

        return "<%s>" % self.html_name

    def render_close(self, parser, node_index):

        tag_data = parser.tag_data
        tag_key = "SimpleTag.%s_nest_level" % self.html_name
        tag_data[tag_key] -= 1

        if tag_data[tag_key] > 0:
            return ''

        return "</%s>" % self.html_name


class DivStyleTag(TagBase):
    """A simple tag that is replaces with a div and a style."""

    def __init__(self, name, style, value, **kwargs):
        super(DivStyleTag, self).__init__(self, name)
        self.style = style
        self.value = value

    def render_open(self, parser, node_index):
        return '<div style="%s:%s;">' % (self.style, self.value)

    def render_close(self, parser, node_index):
        return '</div>'


class LinkTag(TagBase):

    _safe_chars = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-=/&?:%&#')

    _re_domain = re.compile(r"//([a-z0-9-\.]*)", re.UNICODE)

    def __init__(self, name, annotate_links=True, **kwargs):
        super(LinkTag, self).__init__(name, inline=True)
        self.annotate_links = annotate_links

    def render_open(self, parser, node_index):

        self.domain = ''
        tag_data = parser.tag_data
        nest_level = tag_data['link_nest_level'] = tag_data.setdefault('link_nest_level', 0) + 1

        if nest_level > 1:
            return ""

        if self.params:
            url = self.params.strip()
        else:
            url = self.get_contents_text(parser).strip()
            url = _unescape(url)

        self.domain = ""

        if ':' not in url:
            url = 'http://' + url

        scheme, uri = url.split(':', 1)

        if scheme not in ['http', 'https']:
            return ''

        try:
            domain_match = self._re_domain.search(uri.lower())
            if domain_match is None:
                return ''
            domain = domain_match.group(1)
        except IndexError:
            return ''

        domain = domain.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        def percent_encode(s):
            safe_chars = self._safe_chars
            def replace(c):
                if c not in safe_chars:
                    return "%%%02X" % ord(c)
                else:
                    return c
            return "".join([replace(c) for c in s])

        #self.url = percent_encode(url.encode(u'utf-8', u'replace'))
        self.url = percent_encode(url)
        self.domain = domain

        if not self.url:
            return ""

        if self.domain:
            return '<a href="%s">' % PostMarkup.standard_replace_no_break(self.url)
        else:
            return ""


    def render_close(self, parser, node_index):

        tag_data = parser.tag_data
        tag_data['link_nest_level'] -= 1

        if tag_data['link_nest_level'] > 0:
            return ''

        if self.domain:
            return '</a>'+self.annotate_link(self.domain)
        else:
            return ''

    def annotate_link(self, domain=None):

        if domain and self.annotate_links:
            return annotate_link(domain)
        else:
            return ""


class QuoteTag(TagBase):

    def __init__(self, name, **kwargs):
        super(QuoteTag, self).__init__(name, strip_first_newline=True)

    def render_open(self, parser, node_index):
        if self.params:
            return '<blockquote><em>%s</em><br/>' % (PostMarkup.standard_replace(self.params))
        else:
            return '<blockquote>'

    def render_close(self, parser, node_index):
        return "</blockquote>"


class SearchTag(TagBase):

    def __init__(self, name, url, label="", annotate_links=True, **kwargs):
        super(SearchTag, self).__init__(name, inline=True)
        self.url = url
        self.label = label
        self.annotate_links = annotate_links

    def render_open(self, parser, node_idex):

        if self.params:
            search=self.params
        else:
            search=self.get_contents(parser)
        link = '<a href="%s">' % PostMarkup.standard_replace_no_break(self.url)
        if '%' in link:
            return link % quote_plus(search.encode("UTF-8"))
        else:
            return link

    def render_close(self, parser, node_index):

        if self.label:
            if self.annotate_links:
                return '</a>'+ annotate_link(self.label)
            else:
                return '</a>'
        else:
            return ''


class PygmentsCodeTag(TagBase):

    def __init__(self, name, pygments_line_numbers=False, **kwargs):
        super(PygmentsCodeTag, self).__init__(name, enclosed=True, strip_first_newline=True)
        self.line_numbers = pygments_line_numbers

    def render_open(self, parser, node_index):
        contents = self.get_contents(parser).strip('\n')
        self.skip_contents(parser)

        try:
            lexer = get_lexer_by_name(self.params)
        except ClassNotFound:
            contents = _escape(contents)
            return '<div class="code"><pre>%s</pre></div>' % contents

        formatter = HtmlFormatter(linenos=self.line_numbers, cssclass="code")
        hcontents = highlight(contents, lexer, formatter)
        hcontents = hcontents.strip()

        return hcontents


class CodeTag(TagBase):

    def __init__(self, name, **kwargs):
        super(CodeTag, self).__init__(name, enclosed=True, strip_first_newline=True)

    def render_open(self, parser, node_index):
        contents = _escape_no_breaks(self.get_contents(parser))
        self.skip_contents(parser)
        return '<div class="code"><pre>%s</pre></div>' % contents


class ImgTag(TagBase):

    def __init__(self, name, **kwargs):
        super(ImgTag, self).__init__(name, inline=True)

    def open(self, parser, params, *args):
        if params.strip():
            self.auto_close = True
        super(ImgTag, self).open(parser, params, *args)

    def render_open(self, parser, node_index):

        contents = self.get_contents(parser)
        self.skip_contents(parser)

        # Validate url to avoid any XSS attacks
        if self.params:
            url = self.params.strip()
        else:
            url = strip_bbcode(contents)

        url = url.replace('"', "%22").strip()
        if not url:
            return ''
        try:
            scheme, netloc, path, params, query, fragment = urlparse(url)
            if not scheme:
                url = 'http://' + url
                scheme, netloc, path, params, query, fragment = urlparse(url)
        except ValueError:
            return ''
        if scheme.lower() not in ('http', 'https', 'ftp'):
            return ''

        return '<img src="%s"></img>' % PostMarkup.standard_replace_no_break(url)


class ListTag(TagBase):

    def __init__(self, name, **kwargs):
        super(ListTag, self).__init__(name, strip_first_newline=True)
        self.ordered = False

    def render_open(self, parser, node_index):

        self.close_tag = ""
        tag_data = parser.tag_data
        tag_data.setdefault("ListTag.count", 0)

        if tag_data["ListTag.count"]:
            return ""

        tag_data["ListTag.count"] += 1
        tag_data["ListItemTag.initial_item"] = True

        if self.ordered or self.params == "1":
            self.close_tag = "</li></ol>"
            return "<ol><li>"
        elif self.params == "a":
            self.close_tag = "</li></ol>"
            return '<ol style="list-style-type: lower-alpha;"><li>'
        elif self.params == "A":
            self.close_tag = "</li></ol>"
            return '<ol style="list-style-type: upper-alpha;"><li>'
        else:
            self.close_tag = "</li></ul>"
            return "<ul><li>"

    def render_close(self, parser, node_index):

        tag_data = parser.tag_data
        tag_data["ListTag.count"] -= 1

        return self.close_tag


class OrderedListTag(ListTag):
    def __init__(self, name, **kwargs):
        super(OrderedListTag, self).__init__(name, strip_first_newline=True)
        self.ordered = 1


class ListItemTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, auto_close=True)

    def render_open(self, parser, node_index):

        tag_data = parser.tag_data
        if not tag_data.setdefault("ListTag.count", 0):
            return ""

        if tag_data["ListItemTag.initial_item"]:
            tag_data["ListItemTag.initial_item"] = False
            return

        return "</li><li>"


class SizeTag(TagBase):

    valid_chars = frozenset("0123456789")

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index):
        try:
            self.size = int("".join([c for c in self.params if c in self.valid_chars]))
        except ValueError:
            self.size = None

        if self.size is None:
            return ""

        self.size = self.validate_size(self.size)

        return '<span style="font-size:%spx">' % self.size

    def render_close(self, parser, node_index):
        if self.size is None:
            return ""
        return '</span>'

    def validate_size(self, size):
        size = min(64, size)
        size = max(4, size)
        return size


class ColorTag(TagBase):

    valid_chars = frozenset("#0123456789abcdefghijklmnopqrstuvwxyz")
    re_html_color = re.compile(r'[0-9a-f]+')

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index):
        valid_chars = self.valid_chars
        try:
            color = self.params.split()[0].lower()
            self.color = "".join([c for c in color if c in valid_chars])
            if not self.color.startswith('#') and len(self.color) in (3, 6):
                if self.re_html_color.match(self.color):
                    self.color = '#' + self.color
        except IndexError:
            self.color = None

        if not self.color:
            return ""

        return '<span style="color:%s">' % self.color

    def render_close(self, parser, node_index):
        if not self.color:
            return ''
        return '</span>'


class CenterTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index, **kwargs):
        return '<div style="text-align:center;">'

    def render_close(self, parser, node_index):
        return '</div>'


class SectionTag(TagBase):

    """A specialised tag that stores its contents in a dictionary. Can be
    used to define extra contents areas.

    """

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, enclosed=True, strip_first_newline=True)

    def render_open(self, parser, node_index):

        self.section_name = self.params.strip().lower().replace(' ', '_')

        contents = self.get_contents(parser)
        self.skip_contents(parser)

        tag_data = parser.tag_data
        sections = tag_data['output'].setdefault('sections', {})

        sections.setdefault(self.section_name, []).append(contents)

        return ''

class DefaultTag(TagBase):
    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, auto_close=True, inline=True, **kwargs)

    def render_open(self, parser, node_index):
        return _escape(self.get_outer_contents(parser))


def create(include=None,
           exclude=None,
           use_pygments=True,
           default_tag=DefaultTag,
           **kwargs):

    """Create a postmarkup object that converts bbcode to XML snippets. Note
    that creating postmarkup objects is _not_ threadsafe, but rendering the
    html _is_ threadsafe. So typically you will need just one postmarkup instance
    to render the bbcode accross threads.

    include -- List or similar iterable containing the names of the tags to use
               If omitted, all tags will be used
    exclude -- List or similar iterable containing the names of the tags to exclude.
               If omitted, no tags will be excluded
    use_pygments -- If True, Pygments (http://pygments.org/) will be used for the code tag,
                    otherwise it will use <pre>code</pre>
    default_tag -- A tag to use when there is no appropriate tag registered,
    kwargs -- Remaining keyword arguments are passed to tag constructors.

    """

    postmarkup = PostMarkup()
    postmarkup_add_tag = postmarkup.tag_factory.add_tag
    postmarkup.tag_factory.set_default_tag(default_tag)

    def add_tag(tag_class, name, *args, **kwargs):
        if include is None or name in include:
            if exclude is not None and name in exclude:
                return
            postmarkup_add_tag(tag_class, name, *args, **kwargs)

    add_tag(SimpleTag, 'b', 'strong')
    add_tag(SimpleTag, 'i', 'em')
    add_tag(SimpleTag, 'u', 'u')
    add_tag(SimpleTag, 's', 'strike')

    add_tag(LinkTag, 'link', **kwargs)
    add_tag(LinkTag, 'url', **kwargs)

    add_tag(QuoteTag, 'quote')

    add_tag(SearchTag, 'wiki',
            "http://en.wikipedia.org/wiki/Special:Search?search=%s", 'wikipedia.com', **kwargs)
    add_tag(SearchTag, 'google',
            "http://www.google.com/search?hl=en&q=%s&btnG=Google+Search", 'google.com', **kwargs)
    add_tag(SearchTag, 'dictionary',
            "http://dictionary.reference.com/browse/%s", 'dictionary.com', **kwargs)
    add_tag(SearchTag, 'dict',
            "http://dictionary.reference.com/browse/%s", 'dictionary.com', **kwargs)

    add_tag(ImgTag, 'img')
    add_tag(ListTag, 'list')
    add_tag(ListTag, 'ul')
    add_tag(OrderedListTag, 'ol')
    add_tag(ListItemTag, '*')
    add_tag(ListItemTag, 'li')

    add_tag(SizeTag, "size")
    add_tag(ColorTag, "color")
    add_tag(CenterTag, "center")

    if use_pygments:
        assert pygments_available, "Install Pygments (http://pygments.org/) or call create with use_pygments=False"
        add_tag(PygmentsCodeTag, 'code', **kwargs)
    else:
        add_tag(CodeTag, 'code', **kwargs)

    return postmarkup


# http://effbot.org/zone/python-replace.htm
class MultiReplace(object):
    def __init__(self, repl_dict):
        # string to string mapping; use a regular expression
        keys = list(repl_dict.keys())
        keys.sort(reverse=True) # lexical order
        pattern = "|".join([re.escape(key) for key in keys])
        self.pattern = re.compile(pattern)
        self.dict = repl_dict
        self.sub = self.pattern.sub

    def replace(self, s):
        # apply replacement dictionary to string
        get = self.dict.get
        def repl(match):
            item = match.group(0)
            return get(item, item)
        return self.sub(repl, s)

    __call__ = replace


def _escape(s):
    return PostMarkup.standard_replace(s.rstrip('\n'))
escape = _escape

def _escape_no_breaks(s):
    return PostMarkup.standard_replace_no_break(s.rstrip('\n'))

def _unescape(s):
    return PostMarkup.standard_unreplace(s)

_re_dquotes = re.compile(r'''".*?"''')
_re_squotes = re.compile(r"\s'(.+?)'")
def _cosmetic_replace(s):
    s = PostMarkup.cosmetic_replace(s)
    def repl_dquotes(match):
        return "&ldquo;%s&rdquo;" % match.group(0)[1:-1]
    s = _re_dquotes.sub(repl_dquotes, s)
    def repl_squotes(match):
        return " &lsquo;%s&rsquo;" % match.group(1)
    s = _re_squotes.sub(repl_squotes, s)
    return s


class TagFactory(object):

    def __init__(self):
        self.tags = {}

    @classmethod
    def tag_factory_callable(cls, tag_class, name, *args, **kwargs):
        """Returns a callable that returns a new tag instance."""
        def make():
            return tag_class(name, *args, **kwargs)
        return make

    def add_tag(self, cls, name, *args, **kwargs):
        self.tags[name] = self.tag_factory_callable(cls, name, *args, **kwargs)

    def set_default_tag(self, cls):
        self.default_tag = cls

    def __getitem__(self, name):
        return self.tags[name]()

    def __contains__(self, name):
        return name in self.tags

    def get(self, name, default=None):
        if name in self.tags:
            return self.tags[name]()
        return default


class _Parser(object):
    """ This is an interface to the parser, used by Tag classes. """

    def __init__(self, post_markup, tag_data=None):
        self.pm = post_markup
        if tag_data is None:
            self.tag_data = {}
        else:
            self.tag_data = tag_data
        self.render_node_index = 0

    def skip_to_node(self, node_index):
        """ Skips to a node, ignoring intermediate nodes. """
        assert node_index is not None, "Node index must be non-None"
        self.render_node_index = node_index

    def get_text_nodes(self, node1, node2):
        """ Retrieves the text nodes between two node indices. """
        if node2 is None:
            node2 = node1 + 1
        return [node for node in self.nodes[node1:node2] if not callable(node)]

    def begin_no_breaks(self):
        """Disables replacing of newlines with break tags at the start and end of text nodes.
        Can only be called from a tags 'open' method.

        """
        assert self.phase==1, "Can not be called from render_open or render_close"
        self.no_breaks_count += 1

    def end_no_breaks(self):
        """Re-enables auto-replacing of newlines with break tags (see begin_no_breaks)."""
        assert self.phase==1, "Can not be called from render_open or render_close"
        if self.no_breaks_count:
            self.no_breaks_count -= 1


class PostMarkup(object):

    standard_replace = MultiReplace({   '<':'&lt;',
                                        '>':'&gt;',
                                        '&':'&amp;',
                                        '\n':'<br/>'})

    standard_unreplace = MultiReplace({  '&lt;':'<',
                                         '&gt;':'>',
                                         '&amp;':'&'})

    standard_replace_no_break = MultiReplace({  '<':'&lt;',
                                                '>':'&gt;',
                                                '&':'&amp;',})

    cosmetic_replace = MultiReplace({ '--':'&ndash;',
                                      '---':'&mdash;',
                                      '...':'&#8230;',
                                      '(c)':'&copy;',
                                      '(reg)':'&reg;',
                                      '(tm)':'&trade;'
                                    })

    TOKEN_TAG, TOKEN_PTAG, TOKEN_TEXT = list(range(3))

    #_re_tag_on_line = re.compile(r'\[.*?\].*?$', re.MULTILINE)
    _re_tag_on_line = re.compile(r'\[.*?\]', re.UNICODE)
    _re_end_eq = re.compile(r"\]|\=", re.UNICODE)
    _re_quote_end = re.compile(r'\"|\]', re.UNICODE)
    _re_tag_token = re.compile(r'^\[(\S*?)[\s=]\"?(.*?)\"?\]$', re.UNICODE)


    @classmethod
    def tokenize(cls, post):

        re_tag_on_line = cls._re_tag_on_line
        re_end_eq = cls._re_end_eq
        re_quote_end = cls._re_quote_end
        pos = 0

        def find_first(post, pos, re_ff):
            search = re_ff.search(post, pos)
            if search is None:
                return -1
            return search.start()

        TOKEN_TAG, TOKEN_PTAG, TOKEN_TEXT = list(range(3))

        post_find = post.find
        while True:
            brace_pos = find_first(post, pos, re_tag_on_line)
            if brace_pos == -1:
                if pos < len(post):
                    yield TOKEN_TEXT, post[pos:], pos, len(post)
                return
            if brace_pos - pos > 0:
                yield TOKEN_TEXT, post[pos:brace_pos], pos, brace_pos

            pos = brace_pos
            end_pos = pos + 1

            open_tag_pos = post_find('[', end_pos)
            end_pos = find_first(post, end_pos, re_end_eq)
            if end_pos == -1:
                yield TOKEN_TEXT, post[pos:], pos, len(post)
                return

            if open_tag_pos != -1 and open_tag_pos < end_pos:
                yield TOKEN_TEXT, post[pos:open_tag_pos], pos, open_tag_pos
                end_pos = open_tag_pos
                pos = end_pos
                continue

            if post[end_pos] == ']':
                yield TOKEN_TAG, post[pos:end_pos + 1], pos, end_pos + 1
                pos = end_pos + 1
                continue

            if post[end_pos] == '=':
                try:
                    end_pos += 1
                    while post[end_pos] == ' ':
                        end_pos += 1
                    if post[end_pos] != '"':
                        end_pos = post_find(']', end_pos + 1)
                        if end_pos == -1:
                            return
                        yield TOKEN_TAG, post[pos:end_pos + 1], pos, end_pos + 1
                    else:
                        end_pos = find_first(post, end_pos, re_quote_end)
                        if end_pos == -1:
                            return
                        if post[end_pos] == '"':
                            end_pos = post_find('"', end_pos + 1)
                            if end_pos == -1:
                                return
                            end_pos = post_find(']', end_pos + 1)
                            if end_pos == -1:
                                return
                            yield TOKEN_PTAG, post[pos:end_pos + 1], pos, end_pos + 1
                        else:
                            yield TOKEN_TAG, post[pos:end_pos + 1], pos, end_pos
                    pos = end_pos + 1
                except IndexError:
                    return

    @classmethod
    def parse_tag_token(cls, s):
        m = cls._re_tag_token.match(s.lstrip())
        if m is None:
            name, attribs = s[1:-1], ''
        else:
            name, attribs = m.groups()
        if name.startswith('/'):
            return name.strip()[1:].lower(), attribs.strip(), True
        else:
            return name.strip().lower(), attribs.strip(), False

    def add_tag(self, cls, name, *args, **kwargs):
        return self.tag_factory.add_tag(cls, name, *args, **kwargs)

    def tagify_urls(self, postmarkup):
        """ Surrounds urls with url bbcode tags. """

        text_tokens = []
        append = text_tokens.append
        sub = _re_url.sub
        TOKEN_TEXT = PostMarkup.TOKEN_TEXT
        enclosed = False
        tag_factory = self.tag_factory

        enclosed_tags = defaultdict(int)
        for tag_type, tag_token, start_pos, end_pos in self.tokenize(postmarkup):
            if tag_type == TOKEN_TEXT:
                if enclosed:
                    append(tag_token)
                else:
                    append(sub(r"[url]\g<0>[/url]", tag_token))
                    #append(sub(repl, tag_token))
            else:
                tag_name, _tag_attribs, end_tag = self.parse_tag_token(tag_token)

                tag = tag_factory.get(tag_name)
                if tag is not None and tag.enclosed:
                    if end_tag:
                        if tag_name in enclosed_tags:
                            enclosed_tags[tag_name] -= 1
                            if enclosed_tags[tag_name] == 0:
                                del enclosed_tags[tag_name]
                            enclosed = bool(enclosed_tags)
                    else:
                        enclosed_tags[tag_name] += 1
                        enclosed = True

                append(tag_token)

        return "".join(text_tokens)

    def __init__(self, tag_factory=None):
        self.tag_factory = tag_factory or TagFactory()

    def default_tags(self):
        """ Add some basic tags. """
        add_tag = self.tag_factory.add_tag
        add_tag(SimpleTag, 'b', 'strong')
        add_tag(SimpleTag, 'i', 'em')
        add_tag(SimpleTag, 'u', 'u')
        add_tag(SimpleTag, 's', 's')

    def get_supported_tags(self):
        """ Returns a list of the supported tags. """
        return sorted(self.tag_factory.tags.keys())

    # Matches simple blank tags containing only whitespace
    _re_blank_tags = re.compile(r"\<(\w+?)\>\</\1\>")
    _re_blank_with_spaces_tags = re.compile(r"\<(\w+?)\>\s+\</\1\>")

    @classmethod
    def cleanup_html(cls, html):
        """Cleans up html. Currently only removes blank tags, i.e. tags containing only
        whitespace. Only applies to tags without attributes. Tag removal is done
        recursively until there are no more blank tags. So <strong><em></em></strong>
        would be completely removed.

        html -- A string containing (X)HTML

        """
        original_html = ''
        while original_html != html:
            original_html = html
            html = cls._re_blank_tags.sub(" ", html)
            html = cls._re_blank_with_spaces_tags.sub(" ", html)
        html = _re_break_groups.sub("\n", html)
        return html

    def render_to_html(self,
                       post_markup,
                       encoding="ascii",
                       exclude_tags=None,
                       auto_urls=True,
                       paragraphs=False,
                       clean=True,
                       cosmetic_replace=True,
                       render_unknown_tags=False,
                       tag_data=None):

        """Converts post markup (ie. bbcode) to XHTML. This method is threadsafe,
        buy virtue that the state is entirely stored on the stack.

        post_markup -- String containing bbcode.
        encoding -- Encoding of string, defaults to "ascii" if the string is not
        already unicode.
        exclude_tags -- A collection of tag names to ignore.
        auto_urls -- If True, then urls will be wrapped with url bbcode tags.
        paragraphs -- If True then line breaks will be replaced with paragraph
        tags, rather than break tags.
        clean -- If True, html will be run through the cleanup_html method.
        cosmetic_replace -- If True, then some 'smart' quotes will be enabled,
        in addition to replacing some character sequences with html entities.
        tag_data -- An optional dictionary to store tag data in. The default of
        None will create a dictionary internaly. Set this to your own dictionary
        if you want to retrieve information from the Tag Classes.


        """

        if not isinstance(post_markup, str):
            post_markup = str(post_markup, encoding, 'replace')

        if auto_urls:
            post_markup = self.tagify_urls(post_markup)

        post_markup = post_markup.replace('\r\n', '\n')
        if paragraphs:
            post_markup = _re_break_groups.sub('\n\n', post_markup)

        parser = _Parser(self, tag_data=tag_data)
        parser.tag_data.setdefault("output", {})
        parser.markup = post_markup

        if exclude_tags is None:
            exclude_tags = []

        tag_factory = self.tag_factory

        nodes = []
        parser.nodes = nodes

        parser.phase = 1
        parser.no_breaks_count = 0
        enclosed_count = 0
        tag_stack = []
        break_stack = []
        remove_next_newline = False

        def standard_replace(s):
            s = self.standard_replace(s)
            if cosmetic_replace:
                s = _cosmetic_replace(s)
            return s

        def standard_replace_no_break(s):
            s = self.standard_replace_no_break(s)
            if cosmetic_replace:
                s = _cosmetic_replace(s)
            return s

        def check_tag_stack(tag_name):
            for tag in reversed(tag_stack):
                if tag_name == tag.name:
                    return True
            return False

        def redo_break_stack():
            while break_stack:
                tag = break_stack.pop()
                open_tag(tag)
                tag_stack.append(tag)

        def break_inline_tags():
            while tag_stack:
                if tag_stack[-1].inline:
                    tag = tag_stack.pop()
                    close_tag(tag)
                    break_stack.append(tag)
                else:
                    break

        def open_tag(tag):
            def call(node_index):
                return tag.render_open(parser, node_index)
            nodes.append(call)

        def close_tag(tag):
            def call(node_index):
                return tag.render_close(parser, node_index)
            nodes.append(call)

        TOKEN_TEXT = PostMarkup.TOKEN_TEXT

        if paragraphs:
            nodes.append("<p>")

        # Pass 1
        for tag_type, tag_token, start_pos, end_pos in self.tokenize(post_markup):

            if tag_type == TOKEN_TEXT:
                if parser.no_breaks_count:
                    tag_token = tag_token.rstrip()
                    if not tag_token.strip():
                        continue
                if remove_next_newline:
                    tag_token = tag_token.lstrip(' ')
                    if tag_token.startswith('\n'):
                        tag_token = tag_token.lstrip(' ')[1:]
                        if not tag_token:
                            continue
                    remove_next_newline = False

                if tag_stack and tag_stack[-1].strip_first_newline:
                    tag_token = tag_token.lstrip()
                    tag_stack[-1].strip_first_newline = False
                    if not tag_stack[-1]:
                        tag_stack.pop()
                        continue

                if not enclosed_count:
                    redo_break_stack()

                if paragraphs:
                    if not tag_stack:
                        while '\n\n' in tag_token:
                            text, tag_token = tag_token.split('\n\n', 1)
                            if text.strip():
                                nodes.append(standard_replace(text))
                            nodes.append("</p><p>")

                nodes.append(standard_replace(tag_token))
                continue

            tag_name, tag_attribs, end_tag = self.parse_tag_token(tag_token)

            if tag_stack:
                tag_stack[-1].strip_first_newline = False

            if enclosed_count and tag_stack[-1].name != tag_name:
                continue

            if tag_name in exclude_tags:
                continue

            if not end_tag:

                tag = tag_factory.get(tag_name, None)
                if tag is None and render_unknown_tags:
                    tag = tag_factory.default_tag(tag_name)
                if tag is None:
                    continue

                redo_break_stack()

                if not tag.inline:
                    break_inline_tags()

                tag.open(parser, tag_attribs, end_pos, len(nodes), start_pos)
                if tag.enclosed:
                    enclosed_count += 1
                tag_stack.append(tag)

                open_tag(tag)

                if tag.auto_close:
                    tag = tag_stack.pop()
                    tag.close(self, end_pos, len(nodes) - 1)
                    close_tag(tag)

            else:
                if break_stack and break_stack[-1].name == tag_name:
                    break_stack.pop()
                    tag.close(parser, start_pos, len(nodes))
                elif check_tag_stack(tag_name):
                    while tag_stack[-1].name != tag_name:
                        tag = tag_stack.pop()
                        break_stack.append(tag)
                        close_tag(tag)

                    tag = tag_stack.pop()
                    tag.close(parser, start_pos, len(nodes))
                    if tag.enclosed:
                        enclosed_count -= 1

                    close_tag(tag)
                    if paragraphs and not tag.inline and not tag_stack:
                        nodes.append("</p><p>")

                    if not tag.inline:
                        remove_next_newline = True

        if tag_stack:
            redo_break_stack()
            while tag_stack:
                tag = tag_stack.pop()
                tag.close(parser, len(post_markup), len(nodes))
                if tag.enclosed:
                    enclosed_count -= 1
                close_tag(tag)

        if paragraphs:
            nodes.append('</p>')

        parser.phase = 2
        # Pass 2
        parser.nodes = nodes

        text = []
        text_append = text.append
        parser.render_node_index = 0
        while parser.render_node_index < len(parser.nodes):
            i = parser.render_node_index
            node_text = parser.nodes[i]
            if callable(node_text):
                node_text = node_text(i)
            if node_text is not None:
                text_append(node_text)
            parser.render_node_index += 1

        html = "".join(text)
        if clean:
            html = self.cleanup_html(html)
        return html

    # A shortcut for render_to_html
    __call__ = render_to_html


_postmarkup = create(use_pygments=pygments_available, annotate_links=False)
render_bbcode = _postmarkup.render_to_html


def _tests():

    import sys
    #sys.stdout=open('test.htm', 'w')

    post_markup = create(use_pygments=True)

    tests = []
    print("""<link rel="stylesheet" href="code.css" type="text/css" />\n""")

    tests.append(']')
    tests.append('[')
    tests.append(':-[ Hello, [b]World[/b]')

    tests.append("[link=http://www.willmcgugan.com]My homepage[/link]")
    tests.append('[link="http://www.willmcgugan.com"]My homepage[/link]')
    tests.append("[link http://www.willmcgugan.com]My homepage[/link]")
    tests.append("[link]http://www.willmcgugan.com[/link]")

    tests.append("[b]Hello André[/b]")
    tests.append("[google]André[/google]")
    tests.append("[s]Strike through[/s]")
    tests.append("[b]bold [i]bold and italic[/b] italic[/i]")
    tests.append("[google]Will McGugan[/google]")
    tests.append("[wiki Will McGugan]Look up my name in Wikipedia[/wiki]")

    tests.append("[quote Will said...]BBCode is very cool[/quote]")

    tests.append("""[code python]
# A proxy object that calls a callback when converted to a string
class TagStringify(object):
    def __init__(self, callback, raw):
        self.callback = callback
        self.raw = raw
        r[b]=3

    def __str__(self):
        return self.callback()
    def __repr__(self):
        return self.__str__()
[/code]""")


    tests.append("[img]http://upload.wikimedia.org/wikipedia/commons"\
                 "/6/61/Triops_longicaudatus.jpg[/img]")

    tests.append("[list][*]Apples[*]Oranges[*]Pears[/list]")
    tests.append("""[list=1]
    [*]Apples
    [*]Oranges
    are not the only fruit
    [*]Pears
[/list]""")
    tests.append("[list=a][*]Apples[*]Oranges[*]Pears[/list]")
    tests.append("[list=A][*]Apples[*]Oranges[*]Pears[/list]")

    long_test="""[b]Long test[/b]

New lines characters are converted to breaks."""\
"""Tags my be [b]ove[i]rl[/b]apped[/i].

[i]Open tags will be closed.
[b]Test[/b]"""

    tests.append(long_test)


    tests.append("[dict]Will[/dict]")

    tests.append("[code unknownlanguage]10 print 'In yr code'; 20 goto 10[/code]")

    tests.append("[url=http://www.google.com/coop/cse?cx=006850030468302103399%3Amqxv78bdfdo]CakePHP Google Groups[/url]")
    tests.append("[url=http://www.google.com/search?hl=en&safe=off&client=opera&rls=en&hs=pO1&q=python+bbcode&btnG=Search]Search for Python BBCode[/url]")
    #tests = []
    # Attempt to inject html in to unicode
    tests.append("[url=http://www.test.com/sfsdfsdf/ter?t=\"></a><h1>HACK</h1><a>\"]Test Hack[/url]")

    tests.append('Nested urls, i.e. [url][url]www.becontrary.com[/url][/url], are condensed in to a single tag.')

    tests.append('[google]ɸβfvθðsz[/google]')

    tests.append('[size 30]Hello, World![/size]')

    tests.append('[color red]This should be red[/color]')
    tests.append('[color #0f0]This should be green[/color]')
    tests.append("[center]This should be in the center!")

    tests.append('Nested urls, i.e. [url][url]www.becontrary.com[/url][/url], are condensed in to a single tag.')

    #tests = []
    tests.append('[b]Hello, [i]World[/b]! [/i]')

    tests.append('[b][center]This should be centered![/center][/b]')

    tests.append('[list][*]Hello[i][*]World![/i][/list]')


    tests.append("""[list=1]
    [*]Apples
    [*]Oranges
    are not the only fruit
    [*]Pears
[/list]""")

    tests.append("[b]urls such as http://www.willmcgugan.com are authomaticaly converted to links[/b]")

    tests.append("""
[b]
[code python]
parser.markup[self.open_pos:self.close_pos]
[/code]
asdasdasdasdqweqwe
""")

    tests.append("""[list 1]
[*]Hello
[*]World
[/list]""")


    #tests = []
    tests.append("[b][p]Hello, [p]World")
    tests.append("[p][p][p]")

    tests.append("http://www.google.com/search?as_q=bbcode&btnG=%D0%9F%D0%BE%D0%B8%D1%81%D0%BA")

    #tests=["""[b]b[i]i[/b][/i]"""]

    tests = []
    tests.append("[code python]    import this[/code]")

    for test in tests:
        print("<pre>%s</pre>"%str(test.encode("ascii", "xmlcharrefreplace")))
        print("<p>%s</p>"%str(post_markup(test, paragraphs=True).encode("ascii", "xmlcharrefreplace")))
        print("<hr/>")
        print()

    #print repr(post_markup('[url=<script>Attack</script>]Attack[/url]'))

    #print repr(post_markup('http://www.google.com/search?as_q=%D0%9F%D0%BE%D0%B8%D1%81%D0%BA&test=hai'))

    #p = create(use_pygments=False)
    #print (p('[code]foo\nbar[/code]'))

    #print render_bbcode("[b]For the lazy, use the http://www.willmcgugan.com render_bbcode function.[/b]")

    smarkup = create()
    smarkup.add_tag(SectionTag, 'section')

    test = """Hello, World.[b][i]This in italics
[section sidebar]This is the [b]sidebar[/b][/section]
[section footer]
This is the footer
[/section]
More text"""

    print(smarkup(test, paragraphs=True, clean=False))
    tag_data = {}
    print(smarkup(test, tag_data=tag_data, paragraphs=True, clean=True))
    print(tag_data)

