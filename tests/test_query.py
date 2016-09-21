"""
Tests for query parser.

Project: QuasselFlask
"""

from unittest import TestCase
from quasselflask.query_parser import Query, Operator as Op
from logging import Logger
import logging


class TestQuery(TestCase):
    def setUp(self):
        self.logger = Logger('TestQuery', logging.DEBUG)

    def tearDown(self):
        pass

    def test__add_token(self):
        q = Query('', self.logger)
        expected_tokens = []
        self.assertIsNone(q._add_token(list()), "empty char accumulator token: return value")
        self.assertEqual(q.tokens, expected_tokens, "empty char accumulator token: tokens list")

        self.assertIsNone(q._add_token(list('')), "empty string: return value")
        self.assertEqual(q.tokens, expected_tokens, "empty string: tokens list")

        self.assertIsNone(q._add_token(list(' ')), "space: return value")
        self.assertEqual(q.tokens, expected_tokens, "space: tokens list")

        self.assertIsNone(q._add_token(list('  ')), "2 space: return value")
        self.assertEqual(q.tokens, expected_tokens, "2 space: tokens list")

        # non special tokens
        for token in ['a', '1', 'abc', '123', '-', '\\',
                      'ANDES', 'ORRE', 'andes', 'orre', 'Andes', 'ANDes', '(blub', 'blub)', 'asdf\\', '\\(']:
            expected_tokens.append(token)
            self.assertEqual(q._add_token(list(token)), token, "'%s': return value" % token)
            self.assertEqual(q.tokens, expected_tokens, "'%s': tokens list" % token)

        # both kinds of tokens, literals
        for token in ['a', '1', 'abc', '123', '\\', '(', 'ANDes', 'and', 'or', 'AND', 'OR', '(']:
            expected_tokens.append(token)
            self.assertEqual(q._add_token(list(token), True), token, "'%s' literal: return value" % token)
            self.assertEqual(q.tokens, expected_tokens, "'%s' literal: tokens list" % token)

        # special tokens
        for token, result in {'AND': Op.AND, 'OR': Op.OR, 'and': Op.AND, 'or': Op.OR,
                              'aNd': Op.AND, '(': Op.GROUP_OPEN, ')': Op.GROUP_CLOSE}.items():
            expected_tokens.append(result)
            self.assertEqual(q._add_token(list(token)), result, "'%s' literal: return value" % token)
            self.assertEqual(q.tokens, expected_tokens, "'%s' literal: tokens list" % token)

        expected_tokens.append('done')
        self.assertEqual(q._add_token(list('done')), 'done', "'done': return value")
        self.assertEqual(q.tokens, expected_tokens, "'done': tokens list")

    def test__tokenize_escaped(self):
        acc = []

        q = Query('', self.logger)

        # empty string behaviour undefined. Should never be passed: used only while looping over string

        q._tokenize_escaped('x', acc)
        self.assertEqual(acc, ['\\', 'x'], "'x' char")
        acc.clear()

        q._tokenize_escaped('"', acc)
        self.assertEqual(acc, ['"'], "'\"' char")
        acc.clear()

        q._tokenize_escaped('\\', acc)
        self.assertEqual(acc, ['\\'], "'\\' char")
        acc.clear()

        # use totally different values from the defaults to test regressions of hardcoded defaults
        escapables = ['*', '?']
        escape = '`'

        q._tokenize_escaped('x', acc, escapables, escape)
        self.assertEqual(acc, ['`', 'x'], "'x' char")
        acc.clear()

        q._tokenize_escaped('`', acc, escapables, escape)
        self.assertEqual(acc, ['`', '`'], "'`' char")
        acc.clear()

        q._tokenize_escaped('*', acc, escapables, escape)
        self.assertEqual(acc, ['*'], "'*' char")
        acc.clear()

        q._tokenize_escaped('?', acc, escapables, escape)
        self.assertEqual(acc, ['?'], "'*' char")
        acc.clear()

    def test__tokenize_char(self):
        acc0 = ['a', 'b', 'c']
        acc = acc0.copy()
        tokens = []

        q = Query('', self.logger)

        # empty string behaviour undefined. Should never be passed: used only while looping over string

        # delimiter
        quote, esc = q._tokenize_char(' ', acc)
        tokens.append('abc')
        self.assertEqual(q.tokens, tokens, "delimiter: tokens")
        self.assertFalse(acc, "delimiter: accumulator")
        self.assertFalse(quote, "delimiter: return[0]")
        self.assertFalse(esc, "delimiter: return[1]")
        acc = acc0.copy()

        # token delimiter
        quote, esc = q._tokenize_char('(', acc)
        tokens.append('abc')
        tokens.append(Op.GROUP_OPEN)
        self.assertEqual(q.tokens, tokens, "token delimiter: tokens")
        self.assertFalse(acc, "token delimiter: accumulator")
        self.assertFalse(quote, "token delimiter: return[0]")
        self.assertFalse(esc, "token delimiter: return[1]")
        acc = acc0.copy()

        # token delimiter and a special token
        acc = ['a', 'n', 'd']
        quote, esc = q._tokenize_char('(', acc)
        tokens.append(Op.AND)
        tokens.append(Op.GROUP_OPEN)
        self.assertEqual(q.tokens, tokens, "token delimiter: tokens")
        self.assertFalse(acc, "token delimiter: accumulator")
        self.assertFalse(quote, "token delimiter: return[0]")
        self.assertFalse(esc, "token delimiter: return[1]")
        acc = acc0.copy()

        # escape
        quote, esc = q._tokenize_char('\\', acc)
        self.assertEqual(q.tokens, tokens, "escape: tokens")
        self.assertEquals(acc, acc0, "escape: accumulator")
        self.assertFalse(quote, "escape: return[0]")
        self.assertTrue(esc, "escape: return[1]")
        acc = acc0.copy()

        # quote
        quote, esc = q._tokenize_char('"', acc)
        tokens.append('abc')
        self.assertEqual(q.tokens, tokens, "quote: tokens")
        self.assertFalse(acc, "quote: accumulator")
        self.assertTrue(quote, "quote: return[0]")
        self.assertFalse(esc, "quote: return[1]")
        acc = acc0.copy()

        # any other character
        quote, esc = q._tokenize_char('x', acc)
        self.assertEqual(q.tokens, tokens, "char: tokens")
        self.assertEquals(acc, ['a', 'b', 'c', 'x'], "char: accumulator")
        self.assertFalse(quote, "char: return[0]")
        self.assertFalse(esc, "char: return[1]")
        acc = acc0.copy()

    def test_tokenize(self):
        test_set = [
            ('word1', ['word1']),  # non-special token alone
            ('word1  ', ['word1']),  # with trailing space
            ('word1 word2', ['word1', 'word2']),  # two non-special tokens
            ('word1  word2', ['word1', 'word2']),  # two non-special tokens with excess space
            ('word1 OR word2', ['word1', Op.OR, 'word2']),  # infix operator
            ('word1 ANd word2 OR', ['word1', Op.AND, 'word2', Op.OR]),  # with AND and OR ops, arb placement
            ('word1 OR (word2 word3)', ['word1', Op.OR, Op.GROUP_OPEN,
                                        'word2', 'word3', Op.GROUP_CLOSE]),  # Parentheses
            ('word1 and (word2 OR word3)', ['word1', Op.AND, Op.GROUP_OPEN,
                                            'word2', Op.OR, 'word3', Op.GROUP_CLOSE]),  # Parentheses + ops
            ('a(bvc)cde OR f', ['a', Op.GROUP_OPEN, 'bvc', Op.GROUP_CLOSE,
                                'cde', Op.OR, 'f']),  # parens delimit a token
            ('ab\\"cd ef\\\\g', ['ab"cd', 'ef\\g']),  # Escaping
            ('"jump lemon \\" stride" AND ("melancholy OR tremors" OR "iron(III) oxide \\"AND FLUG\\"")',
                    ['jump lemon \" stride', Op.AND, Op.GROUP_OPEN,
                     'melancholy OR tremors', Op.OR, 'iron(III) oxide "AND FLUG"',
                     Op.GROUP_CLOSE]),  # quotation marks group and suppress special tokens; escaping in quotes
            ('germany"austria blup"', ['germany', 'austria blup']),  # Quotation marks delimit a token
        ]

        for test_string, expected_result in test_set:
            q = Query(test_string, self.logger)
            q.tokenize()
            self.assertEqual(q.tokens, expected_result, "Test string: %s" % test_string)

    def test__parse_process_operator(self):
        q = Query('', self.logger)

        # Test Op.GROUP_OPEN
        # setup string: "word1 AND word2 OR ( ..."
        op_stack = [Op.OR]
        output = ['word1', 'word2', Op.AND]
        q._parse_process_operator(Op.GROUP_OPEN, op_stack, output)
        self.assertEqual(op_stack, [Op.OR, Op.GROUP_OPEN], '( operator: op_stack')
        self.assertEqual(output, ['word1', 'word2', Op.AND], '( operator: output')

        # Test Op.GROUP_CLOSE
        # setup string: "word1 AND word2 OR (word3 OR word4 AND word5) ..."
        op_stack = [Op.OR, Op.GROUP_OPEN, Op.OR, Op.AND]
        output = ['word1', 'word2', Op.AND, 'word3', 'word4', 'word5']
        q._parse_process_operator(Op.GROUP_CLOSE, op_stack, output)
        self.assertEqual(op_stack,
                         [Op.OR],
                         ') operator: op_stack')
        self.assertEqual(output,
                         ['word1', 'word2', Op.AND, 'word3', 'word4', 'word5', Op.AND, Op.OR],
                         ') operator: output')

        # Test Op.GROUP_CLOSE
        # setup string: "word1 OR word2)" - expect implicit parenthesis at the beginning
        op_stack = [Op.OR]
        output = ['word1', 'word2']
        q._parse_process_operator(Op.GROUP_CLOSE, op_stack, output)
        self.assertEqual(op_stack, [], ') operator (mismatched): op_stack')
        self.assertEqual(output, ['word1', 'word2', Op.OR], ') operator (mismatched): output')

        # Test Op.AND, Op.OR
        # setup string: "word1 AND word2 AND ..." - left associativity
        op_stack = [Op.AND]
        output = ['word1', 'word2']
        q._parse_process_operator(Op.AND, op_stack, output)
        self.assertEqual(op_stack, [Op.AND], 'AND associativity: op_stack')
        self.assertEqual(output, ['word1', 'word2', Op.AND], 'AND associativity: output')

        # setup string: "word1 OR word2 OR ..." - left associativity
        op_stack = [Op.OR]
        output = ['word1', 'word2']
        q._parse_process_operator(Op.OR, op_stack, output)
        self.assertEqual(op_stack, [Op.OR], 'OR associativity: op_stack')
        self.assertEqual(output, ['word1', 'word2', Op.OR], 'OR associativity: output')

        # setup string: "word1 AND word2 OR ..." - AND precedence 1
        op_stack = [Op.AND]
        output = ['word1', 'word2']
        q._parse_process_operator(Op.OR, op_stack, output)
        self.assertEqual(op_stack, [Op.OR], 'AND precedence 1: op_stack')
        self.assertEqual(output, ['word1', 'word2', Op.AND], 'AND precedence 1: output')

        # setup string: "word1 OR word2 AND ..." - AND precedence 2
        op_stack = [Op.OR]
        output = ['word1', 'word2']
        q._parse_process_operator(Op.AND, op_stack, output)
        self.assertEqual(op_stack, [Op.OR, Op.AND], 'AND precedence 2: op_stack')
        self.assertEqual(output, ['word1', 'word2'], 'AND precedence 2: output')

    def test_parse_basic(self):
        test_set = [
            (['word1', Op.AND, 'word2'], ['word1', 'word2', Op.AND]),  # binary AND

            (['word1', Op.OR, 'word2'], ['word1', 'word2', Op.OR]),  # binary OR

            (['word1', Op.AND, 'word2', Op.AND, 'word3'],
                ['word1', 'word2', Op.AND, 'word3', Op.AND]),  # three input AND

            (['word1', Op.OR, 'word2', Op.OR, 'word3'],
             ['word1', 'word2', Op.OR, 'word3', Op.OR]),  # three input OR

            (['word1', Op.AND, 'word2', Op.OR, 'word3'],
                ['word1', 'word2', Op.AND, 'word3', Op.OR]),  # AND precedence over OR #1

            (['word1', Op.OR, 'word2', Op.AND, 'word3'],
                ['word1', 'word2', 'word3', Op.AND, Op.OR]),  # AND precedence over OR #2

            (['word1', Op.AND, Op.GROUP_OPEN, 'word2', Op.OR, 'word3', Op.GROUP_CLOSE],
                ['word1', 'word2', 'word3', Op.OR, Op.AND]),  # Parenthesis vs. precedence #1

            (['word1', Op.OR, Op.GROUP_OPEN, 'word2', Op.AND, 'word3', Op.GROUP_CLOSE],
             ['word1', 'word2', 'word3', Op.AND, Op.OR]),  # Parenthesis vs. precedence #2

            ([Op.GROUP_OPEN, 'word1', Op.AND, 'word2', Op.GROUP_CLOSE, Op.OR, 'word3'],
             ['word1', 'word2', Op.AND, 'word3', Op.OR]),  # Redundant parentheses

            (['word1', Op.OR, Op.GROUP_OPEN, 'word2', Op.AND, 'word3', Op.OR,
              Op.GROUP_OPEN, 'word4', Op.AND, 'word5', Op.OR, 'word6',
              Op.GROUP_CLOSE, Op.GROUP_CLOSE, Op.OR, 'word7'],
                ['word1', 'word2', 'word3', Op.AND, 'word4', 'word5', Op.AND, 'word6', Op.OR,
                 Op.OR, Op.OR, 'word7', Op.OR]),  # a bit of nesting
        ]
        self._exec_parse_set(test_set)

    def test_parse_malformed(self):
        """
        A parsing test for malformed inputs and implicit inputs. The intention is to verify that, in cases where a
        meaningful interpretation is still possible, the parser degrades gracefully.
        :return:
        """
        test_set = [
            # Missing parentheses
            (['word1', Op.OR, Op.GROUP_OPEN, 'word2', Op.AND, 'word3', Op.OR,
              Op.GROUP_OPEN, 'word4', Op.AND, 'word5', Op.OR, 'word6', Op.GROUP_CLOSE],
             ['word1', 'word2', 'word3', Op.AND, 'word4', 'word5', Op.AND, 'word6', Op.OR,
              Op.OR, Op.OR]),  # nesting with a missing close parenthesis

            (['word1', Op.OR, 'word2', Op.GROUP_CLOSE, Op.AND, Op.GROUP_OPEN, 'word3', Op.OR, 'word4'],
             ['word1', 'word2', Op.OR, 'word3', 'word4', Op.OR, Op.AND]),  # missing open and close parens (diff groups)

            # Missing arguments
            ([Op.OR, 'word1', Op.OR, 'word2'], ['word1', Op.OR, 'word2']),  # (malformed) unary pre-OR

            (['word1', Op.OR, 'word2', Op.OR], ['word1', 'word2', Op.OR]),  # (malformed) unary post-OR

            (['word1', Op.OR, Op.GROUP_OPEN, Op.OR, 'word2', Op.OR, 'word3', Op.GROUP_CLOSE],
             ['word1', 'word2', Op.OR, 'word3', Op.OR, Op.OR]),  # (malformed) unary pre-OR parens

            (['word1', Op.OR, Op.GROUP_OPEN, 'word2', Op.OR, 'word3', Op.OR, Op.GROUP_CLOSE],
             ['word1', 'word2', Op.OR, 'word3', Op.OR, Op.OR]),  # (malformed) unary post-OR parens

            # Parenthesis weirdness
            (['word1', Op.AND, 'word2', Op.GROUP_OPEN, Op.GROUP_CLOSE, Op.OR, 'word3'],
             ['word1', 'word2', Op.AND, 'word3', Op.OR]),  # empty parentheses in an otherwise good statement

            (['word1', Op.AND, 'word2', Op.GROUP_OPEN, Op.GROUP_CLOSE, 'word3'],
             ['word1', 'word2', Op.AND, 'word3', Op.AND]),  # empty parentheses in an implicit AND position

            ([Op.GROUP_CLOSE, 'word1', Op.AND, 'word2', Op.OR, 'word3', Op.GROUP_OPEN],
             ['word1', 'word2', Op.AND, 'word3', Op.OR]),  # unmatched parentheses at the ends

            # Implicit AND behaviours
            (['word1', 'word2', Op.AND, 'word3'],
             ['word1', 'word2', Op.AND, 'word3', Op.AND]),  # implicit AND between word tokens

            (['word1', Op.GROUP_OPEN, 'word2', Op.AND, 'word3', Op.GROUP_CLOSE],
             ['word1', 'word2', 'word3', Op.AND, Op.AND]),  # implicit AND between word and paren

            ([Op.GROUP_OPEN, 'word1', Op.AND, 'word2', Op.GROUP_CLOSE, 'word3'],
             ['word1', 'word2', Op.AND, 'word3', Op.AND]),  # implicit AND between paren and word

            ([Op.GROUP_OPEN, 'word1', Op.AND, 'word2', Op.GROUP_CLOSE,
              Op.GROUP_OPEN, 'word3', Op.AND, 'word4', Op.GROUP_CLOSE],
             ['word1', 'word2', Op.AND, 'word3', 'word4', Op.AND, Op.AND]),  # implicit AND between paren and paren
        ]
        self._exec_parse_set(test_set)

    def _exec_parse_set(self, test_set):
        """
        Given a test set as described below, executes all tests against the Query.parse() routine.
        :param test_set: A list of tuples of the form ([list of input tokens], [list of parsed tokens]). Input tokens
            corresponds to self.tokens after tokenized(); parsed tokens correspond to self.postfix after parse() and
            represent the same query in postfix (rather than infix) format.
        :return:
        """
        for test_tokens, expected_result in test_set:
            q = Query('', self.logger)
            q.tokens = test_tokens
            q.parse()
            self.assertEqual(q.postfix, expected_result, "Test input: %s" % repr(test_tokens))

    def test_eval(self):
        self.fail()
