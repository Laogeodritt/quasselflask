"""
Query parsing tools

Project: QuasselFlask
"""
# TODO: update docstring

from enum import Enum
from logging import Logger


class Operator(Enum):
    AND = 0
    OR = 1
    GROUP_OPEN = 2
    GROUP_CLOSE = 3


class Query(object):
    """
    Parser for binary search queries (Google-like). Supports:

    * AND and OR operators (left-associative, AND has higher precedence)
    * Implicit AND of multiple space-separated words
    * Ignores misplaced operators (e.g. beginning/end of a parenthetical group or of the entire string)
    * Parenthesis grouping
    * String literals using double-quotes (can be used to match parentheses and the words AND/OR too)
    * Escaped double-quote literal '\"' and escaped backslash literal '\\'

    Usage: Construct with the query string, call tokenize(), call parse().

    Now the query is ready to be evaluated using eval() and your own callback functions to evaluate the results. You
    could alternatively get the raw postfix token array using get_parsed(), which is very simple to evaluate manually
    by iterating over the tokens and using a single stack - this can be useful for more complex evaluations.
    """
    # See the property getters below for documentation on these maps
    _operator_map = {
        'AND': Operator.AND,
        'OR': Operator.OR,
        '(': Operator.GROUP_OPEN,
        ')': Operator.GROUP_CLOSE,
    }

    # See the property getters below for documentation on these maps
    _operator_precedence = {
        Operator.AND: 100,
        Operator.OR: 50,
    }

    @property
    def operator_map(self) -> {str: Operator}:
        """
        Read-only property: mapping of strings to Operator token objects. A copy is returned.
        """
        return self._operator_map.copy()

    @property
    def operator_precedence(self) -> {Operator: int}:
        """
        Read-only property: mapping of Operator token objects to their precedence value (higher = higher precedence).
        `str` represents a normal string token.
        A copy is returned.
        """
        return self._operator_precedence.copy()

    def __init__(self, query_string: str, logger: Logger=None):
        self.string = query_string
        self.tokens = []
        self.postfix = []
        self.logger = logger.getChild('query_parser')

    def get_tokens(self):
        """
        Get a copy of the tokenized query. If tokenize() hasn't been run or failed, this will be an empty list.
        :return: Tokenised query
        """
        return self.tokens.copy()

    def get_parsed(self):
        """
        Get a copy of the query after parsing to postfix. This form is ready to be evaluated. If parse() hasn't been
        run or failed, this will be an empty list.
        :return:
        """
        return self.postfix.copy()

    def tokenize(self):
        """
        Tokenize the input.
        :return: None
        """
        self.tokens.clear()
        accumulator = []
        in_quotes = False
        in_escape = False

        for c in self.string:
            if in_quotes:
                if in_escape:  # only \ and " escapable
                    self._tokenize_escaped(c, accumulator)
                    in_escape = False
                else:  # in quotes, out of escape: special chars " and \
                    cur_quote, cur_escape = self._tokenize_char(c, accumulator, delimiters=[], tokens=[])
                    in_quotes = not cur_quote  # if cur_quote, exit the quoted context
                    in_escape = cur_escape
            else:  # not in quotes: special chars " ( ) and space
                if in_escape:  # space is not escapable and still a token boundary
                    if c == ' ':  # exception to escape processing: ' ' not escapable
                        accumulator.append('\\')
                        self._add_token(accumulator)
                    else:
                        self._tokenize_escaped(c, accumulator)
                    in_escape = False
                else:  # out of escape: special chars " ( ) \ and space
                    cur_quote, cur_escape = self._tokenize_char(c, accumulator)
                    in_quotes = cur_quote
                    in_escape = cur_escape
        # save anything left in accumulator - probably a last token if anything
        self._add_token(accumulator)

    def _tokenize_char(self, c: str, accumulator: [str],
                       delimiters=None, tokens=None, escape='\\', quote='"'):
        """
        Process a character during tokenization, outside special contexts.

        :param c: current character being processed
        :param accumulator: current token accumulator
        :param delimiters: token delimiters (which aren't tokens themselves), default [' ']
        :param tokens: token delimiters which also act as single-char tokens themselves; default ['(', ')']
        :param escape: the escape character
        :param quote: the quote character
        :return: (is_quote, is_escape)
        """
        is_quote = False
        is_escape = False

        # set defaults (not in defaults list b/c mutable)
        if delimiters is None:
            delimiters = [' ']
        if tokens is None:
            tokens = ['(', ')']

        if c in delimiters:
            self._add_token(accumulator)
        elif c in tokens:  # delimits prev. token and is a token in itself
            self._add_token(accumulator)
            self._add_token([c])
        elif c in escape:  # doesn't delimit token, only affects processing of next char (don't add token)
            is_escape = True
        elif c in quote:  # delimits a token
            self._add_token(accumulator)
            is_quote = True
        else:  # not a delimiter or special character class
            accumulator.append(c)
        return is_quote, is_escape

    def _tokenize_escaped(self, c: str, accumulator: [str], escapables=('"', '\\'), escape='\\'):
        """
        During tokenization, process a character while in an escaped context.
        Escapable characters are appended to the accumulator as-is; non-escapable characters are
        appended to the accumulator preceded by the escape character.

        Caller should remember to update escaped context to False (as escapes only affect the next
        character).

        :param c: Character being processed during tokenization
        :param accumulator: Current accumulator. May be modified by this method.
        :param escapables: list of escapable chars
        :param escape: escape char
        :return: None
        """
        if c in escapables:
            accumulator.append(c)
        else:
            accumulator.append(escape)
            accumulator.append(c)

    def _add_token(self, token_list: [str], literal=False):
        """
        Add token to self.tokens and clear token_list; should only be called by tokenize().
        :param token_list: The token to add, as a list of characters.
        :param literal: If True, suppress operator detection and insert the text as passed.
        :return: The resolved token (either a string or an Operator enum value). This will already be appended to
                self.tokens and must not be appended by the caller. If the token passed is empty or only whitespace,
                then no token is added to self.tokens and None is returned.
        """
        token_str = ''.join(token_list)
        token_list.clear()

        # Blank token
        if not token_str or token_str.isspace():
            return None

        # Check if regular text token or operator keyword
        if not literal and token_str.upper() in self._operator_map.keys():
            token = self._operator_map.get(token_str.upper())
        else:
            token = token_str

        self.tokens.append(token)
        return token

    def parse(self):
        """
        Just this: https://en.wikipedia.org/wiki/Shunting-yard_algorithm

        Read that. It'll be far clearer than the implementation code. I'm pretty much just following the algorithm in
        my implementation here, except that I reordered some of the conditionals. There are some checks, which are
        commented, to ensure a correct grammar and to implicitly correct certain malformed inputs, as the algorithm
        as described in the link assumes correctly formed inputs to begin with.

        This implementation is simplified because:
            * There are no functions
            * Only two operators, AND and OR, of different precedence and left-associative, are supported



        Requires self.tokens to be populated and operators to be elements of the Operator enum
        """

        #  TODO An extended feature from the shunting yard (commented as necessary):
        # * Consecutive words have an implicit AND.
        op_stack = []
        output = []

        for token in self.tokens:
            if isinstance(token, Operator):
                self._parse_process_operator(token, op_stack, output)
            else:  # non-operator token
                output.append(token)

        # once all tokens processed, take care of remaining op_stack
        try:
            while True:
                op_pop = op_stack.pop()
                if op_pop is not Operator.GROUP_OPEN:
                    output.append(op_pop)
                else:
                    # mismatched parentheses - an open parenthesis never closed
                    # assume an implicit closing parenthesis at the end - no need to do anything
                    self.logger.warning("Mismatched '(' in query: %s", self.string)
        except IndexError:
            pass  # empty op_stack - this is normal

        self.postfix = output

    def _parse_process_operator(self, op: Operator, op_stack: [str], output: list):
        """
        :param op: current Operator token
        :param op_stack: current operator stack - may be modified by this method
        :param output: current output - may be modified by this method
        :return: None
        """
        if op is Operator.GROUP_OPEN:
            op_stack.append(op)
        elif op is Operator.GROUP_CLOSE:
            op_pop = op_stack.pop()
            while op_pop is not Operator.GROUP_OPEN:  # find the matching opening parenthesis
                output.append(op_pop)  # GROUP_OPEN will never be appended to output
                try:
                    op_pop = op_stack.pop()
                except IndexError:
                    op_pop = Operator.GROUP_OPEN  # if mismatched parens, assume paren at beginning
                    self.logger.warning("Unmatched ')' in query: %s", self.string)
        else:  # any other operator
            try:
                while op_stack[-1] is not Operator.GROUP_OPEN and op_stack[-1] is not Operator.GROUP_CLOSE and \
                                self._operator_precedence[op] <= self._operator_precedence[op_stack[-1]]:
                    # AND, OR both left-associative so we only need to check this <= case
                    output.append(op_stack.pop())
            except IndexError:  # empty op_stack
                pass  # This is OK - popping entire op_stack is equivalent to hitting GROUP_OPEN
            op_stack.append(op)

    def eval(self, and_func=None, or_func=None):
        """
        Evaluate the processed query, once tokenization + infix conversion is completed.

        For all callbacks: The callback must return the result of the operator. The arguments passed to the callback may
        be string tokens (as processed in this class), or the result object from a previous callback call, or any
        combination thereof.

        :param and_func: Callback taking two arguments for the AND function.
        :param or_func: Callback taking two operands for the OR function.
        :return: The final result of evaluation
        :raise ValueError: unexpected tokens or insufficient operands. In the case of an error being raised, it is the
                caller's responsibility to clean up the expression execution that was occurring via the callbacks.
        """

        #
        # FIXME: Unary AND/OR should be silently ignored (malformed input:
        # AND/OR at beginning/end of string or parenthetical)
        #
        arg_queue = []
        token = None
        try:
            for token in self.postfix:
                if not isinstance(token, Operator):
                    arg_queue.append(token)
                else:
                    if token is Operator.AND:
                        arg_queue.append(and_func(arg_queue.pop(), arg_queue.pop()))
                    elif token is Operator.OR:
                        arg_queue.append(or_func(arg_queue.pop(), arg_queue.pop()))
                    else:
                        ValueError('Unexpected operator %s during eval', token.name)
            if len(arg_queue) != 1:
                raise ValueError('Orphaned operands during eval')
        except IndexError:
            raise ValueError('Insufficient operands for operator %s during eval', token.name)

