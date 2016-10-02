"""
Query parsing tools.

Project: QuasselFlask
"""

from enum import Enum
from logging import Logger


class Operator(Enum):
    AND = 0x0
    OR = 0x1
    GROUP_OPEN = 0x2
    GROUP_CLOSE = 0x3
    # Special types used for defining the grammar
    START = 0x80
    END = 0x81
    REMOVE_FIRST = 0xc6
    REMOVE_NEXT = 0xc7
    REMOVE_BOTH = 0xc8


class BooleanQuery(object):
    """
    Parser for boolean search queries (Google-like). Supports:

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

    I should probably replace this with a PLY implementation instead. But it was fun to make!
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

    # See the property getters below for documentation on these maps
    _operator_rules = {
        Operator.START: {
            Operator.AND: Operator.REMOVE_NEXT,
            Operator.OR: Operator.REMOVE_NEXT,
            Operator.GROUP_CLOSE: Operator.REMOVE_NEXT,
        },
        str: {
            str: Operator.AND,
            Operator.GROUP_OPEN: Operator.AND,
        },
        Operator.AND: {
            Operator.AND: Operator.REMOVE_FIRST,
            Operator.OR: Operator.REMOVE_FIRST,
            Operator.GROUP_CLOSE: Operator.REMOVE_FIRST,
            Operator.END: Operator.REMOVE_FIRST,
        },
        Operator.OR: {
            Operator.AND: Operator.REMOVE_NEXT,
            Operator.OR: Operator.REMOVE_FIRST,
            Operator.GROUP_CLOSE: Operator.REMOVE_FIRST,
            Operator.END: Operator.REMOVE_FIRST,
        },
        Operator.GROUP_OPEN: {
            Operator.AND: Operator.REMOVE_NEXT,
            Operator.OR: Operator.REMOVE_NEXT,
            Operator.GROUP_CLOSE: Operator.REMOVE_BOTH,
            Operator.END: Operator.REMOVE_FIRST
        },
        Operator.GROUP_CLOSE: {
            Operator.GROUP_OPEN: Operator.AND,
            str: Operator.AND,
        },
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

    @property
    def operator_rules(self) -> {Operator: ([Operator], Operator)}:
        """
        Read-only property: two-layer dict of Operator `first_token` to: `{next_token: correction_token}`. Defines
        pairs of tokens (first_token, next_token) that are NOT ALLOWED to be consecutive, and the correction that can
        be made to implicitly fix the situation.

        * next_token is a token or type of token which CANNOT immediately follow `first_token`.
        * `correction_token` is the token that can be used to correct the situation. It is inserted between
            `first_token` and `next_token`.

        `first_token` and `next_token` can take on some special values:

        * `str` (the object) represents a normal string token.
        * Operator.BEGIN: For the beginning of a string. Can only be `first_token` (for obvious reasons).
        * Operator.END: For the end of a strong. Can only be `next_token` (for obvious reasons).

        Correction tokens are usually Operator enum values, but may take on special tokens:
        *

        A copy is returned.
        """
        return self._operator_rules.copy()

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

        :param c: current character being processed. Note that a whitespace character is handled specially: it is
            considered equivalent to a space, and if it is added to the output it will be converted to a space 0x20.
        :param accumulator: current token accumulator
        :param delimiters: token delimiters (which aren't tokens themselves), default [' '].
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

        if c.isspace():  # all whitespace treated as spaces
            c = ' '

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

        if c.isspace():  # all whitespace treated as spaces
            c = ' '

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
        self.parse_grammar()
        self.parse_postfix()

    def parse_grammar(self):
        """
        Checks the grammar of the tokenized strings, and applies certain corrections to allow graceful degradation of
        malformed inputs, per the `self._operator_rules`.

        I feel as if the fact that I'm massaging based on a two-token context means I'm in over my head and should
        go grab a lex/yacc implementation. On the other hand, I'm not sure about the malformed input resilience with
        that---I guess I can possibly define certain token combinations like '( AND' as valid expressions that evaluate
        to their corrected value '('?

        TODO: It might be possible to integrate this resilience, along the same lines as above, into the main parser
        algorithm (parse_postfix) - need to think about these cases more and/or test against the test cases:

        * Implicit 'AND' before a string: observation, when pushing strings to output, the total operators (except
            parentheses) is one less than the total words [in both output and op_stack].
            Does this always hold true? Thinking about 'word1 AND word2 AND word3' or 'word1 AND (word2 AND word3)'
            right now and seems OK. If an AND is missing, this can be detected and an AND can be pushed to the op stack
            before pushing the string to the output.
        * Implicit 'AND' before an opening parenthesis: consider the open parenthesis like a string
        * Double operators: Similar observation as above: when processing an operator (before pushing), total operators
            (excluding parens) is one less than total words. If adding too many operators exceeds this, then either the
            top operator of the stack should be replaced with the current operator, or the current operator discarded.
        * Accidentally unary ANDs and ORs detects like double operators, current operator should be dropped?
        * Empty parentheses '()' are fine: parse algorithm will drop them immediately. What about the case
            'word1 () OR word2'? An implicit 'AND' is inserted before word1 because we haven't seen the OR yet...
            (also consider the case 'word1 (AND AND AND) OR word2', where the ANDs in the parens should be dropped by
            the above algorithm). Solution: re-implement "correction" detection? (Maybe easier to implement as
            Operator.AND_IMPLICIT rather than storing a boolean for it.)
        :return: None
        """
        new_tokens = [Operator.START]
        new_tokens_corr = [False]
        rules = self._operator_rules
        for token in self.tokens:
            self._parse_grammar_token(token, new_tokens, new_tokens_corr, rules)
        self._parse_grammar_token(Operator.END, new_tokens, new_tokens_corr, rules)
        self.tokens = new_tokens

    def _parse_grammar_token(self, token, accumulator: list, accumulator_corrections: [bool],
                             rules: {Operator: {Operator: Operator}}):
        while True:  # loop allows continuous rechecking when REMOVE_FIRST rules modifies the sequence
            try:
                last_token = accumulator[-1] if isinstance(accumulator[-1], Operator) else str
                next_token = token if isinstance(token, Operator) else str
                corrector = rules[last_token][next_token]
                # remove correctors that broke things as priority
                if (corrector is Operator.REMOVE_FIRST or
                        corrector is Operator.REMOVE_NEXT or
                        corrector is Operator.REMOVE_BOTH)\
                        and accumulator_corrections[-1]:
                    accumulator.pop()
                    accumulator_corrections.pop()
                elif corrector is Operator.REMOVE_FIRST:
                    accumulator.pop()
                    accumulator_corrections.pop()
                    continue  # new token sequence in the accumulator - let's check it
                elif corrector is Operator.REMOVE_NEXT:
                    return  # we drop the "next" token - move on to the one after that
                elif corrector is Operator.REMOVE_BOTH:
                    accumulator.pop()  # drop the "last" token
                    accumulator_corrections.pop()
                    return  # also drop the "next" token and move on
                else:
                    accumulator.append(corrector)
                    accumulator_corrections.append(True)
                    accumulator.append(token)
                    accumulator_corrections.append(False)
                    return  # after corrective insertion, we're done with this token
            except KeyError:  # this means it's an acceptable combination (no corrective rules exist)
                accumulator.append(token)
                accumulator_corrections.append(False)
                return  # finished with this token
            except IndexError:  # new_tokens is empty because of REMOVE_FIRST rules
                # unusual situation (because there's should be a REMOVE_FIRST rule on Operator.START)
                # but we'll run with it and assume it's normal
                accumulator.append(token)
                accumulator_corrections.append(False)
                return  # finished with this token

    def parse_postfix(self):
        """
        Just this: https://en.wikipedia.org/wiki/Shunting-yard_algorithm

        Read that. It'll be far clearer than the implementation code. I'm pretty much just following the algorithm in
        my implementation here, except that I reordered some of the conditionals. There are some checks, which are
        commented, to ensure a correct grammar and to implicitly correct certain malformed inputs, as the algorithm
        as described in the link assumes correctly formed inputs to begin with.

        This implementation is simplified because:
            * There are no functions
            * Only two operators, AND and OR, of different precedence and left-associative, are supported

        Requires self.tokens to be populated (via tokenize()) and operators to be elements of the Operator enum.
        parse_grammar() should be run first to verify the grammar and implement certain corrections to allow for
        graceful degradation of malformed inputs.
        """
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

    def _parse_process_token(self, token_queue: list, op_stack: [str], output: list):
        """
        :param token_queue: current token queue, [current_token, next_token]
        :param op_stack: current operator stack - may be modified by this method
        :param output: current output - may be modified by this method
        :return: None
        """
        if isinstance(token_queue[0], Operator):
            self._parse_process_operator(token_queue[0], op_stack, output)
        else:  # non-operator token
            output.append(token_queue[0])

    def _parse_process_operator(self, op: Operator, op_stack: [str], output: list):
        """
        During parse, processes an operator token.
        :param op: current Operator token
        :param op_stack: current operator stack - may be modified by this method
        :param output: current output - may be modified by this method
        :return: None
        """
        # Operator values that don't do anything (markers for operator rules checking mostly)
        if op is Operator.START or op is Operator.END\
                                or op is Operator.REMOVE_FIRST or op is Operator.REMOVE_NEXT:
            return

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

    def eval(self, and_func=None, or_func=None, operand_wrapper=None):
        """
        Evaluate the processed query, once tokenization + infix conversion is completed.

        For all callbacks: The callback must return the result of the operator. The arguments passed to the callback may
        be string tokens (as processed in this class), or the result object from a previous callback call, or any
        combination thereof.

        :param and_func: Callback taking two arguments for the AND function.
        :param or_func: Callback taking two operands for the OR function.
        :param operand_wrapper: Callback that is called on all operands before AND and OR operations (including operands
            that are evaluated from AND/OR). Useful if all operands need a conversion before being passed to AND/OR
            (but make sure to guard against reconverting an already AND'd or OR'd result). Must return the value that is
            to be passed to AND/OR functions or returned as the expression evaluation result.
        :return: The final result of evaluation
        :raise ValueError: unexpected tokens or insufficient operands. In the case of an error being raised, it is the
                caller's responsibility to clean up the expression execution that was occurring via the callbacks.
        """
        arg_queue = []
        token = None
        if not self.postfix:
            return None
        if operand_wrapper is None:
            def noop(s): pass
            operand_wrapper = noop
        try:
            for token in self.postfix:
                if not isinstance(token, Operator):
                    arg_queue.append(operand_wrapper(token))
                else:
                    if token is Operator.AND:
                        arg_queue.append(and_func(arg_queue.pop(), arg_queue.pop()))
                    elif token is Operator.OR:
                        arg_queue.append(or_func(arg_queue.pop(), arg_queue.pop()))
                    else:
                        ValueError('Unexpected operator %s during eval', token.name)
            if len(arg_queue) != 1:
                raise ValueError('Orphaned operands during eval')
            return arg_queue[0]

        except IndexError:
            raise ValueError('Insufficient operands for operator %s during eval', token.name)
