"""
Tests for bitarray.util module
"""
from __future__ import absolute_import

import os
import re
import sys
import base64
import binascii
import shutil
import tempfile
import unittest
from string import hexdigits
from random import choice, randint, random
from collections import Counter

from bitarray import (bitarray, frozenbitarray, decodetree,
                      get_default_endian, _set_default_endian)
from bitarray.test_bitarray import Util, skipIf

from bitarray.util import (
    zeros, urandom, pprint, make_endian, rindex, strip, count_n,
    parity, count_and, count_or, count_xor, subset,
    serialize, deserialize, ba2hex, hex2ba, ba2base, base2ba,
    ba2int, int2ba, vl_encode, vl_decode,
    huffman_code, canonical_huffman, canonical_decode,
)

if sys.version_info[0] == 3:
    from io import StringIO
else:
    from io import BytesIO as StringIO

tests = []  # type: list

# ---------------------------------------------------------------------------

class TestsZeros(unittest.TestCase):

    def test_basic(self):
        for default_endian in 'big', 'little':
            _set_default_endian(default_endian)
            a = zeros(0)
            self.assertEqual(a, bitarray())
            self.assertEqual(a.endian(), default_endian)

            a = zeros(0, endian=None)
            self.assertEqual(len(a), 0)
            self.assertEqual(a.endian(), default_endian)

            for n in range(100):
                a = zeros(n)
                self.assertEqual(len(a), n)
                self.assertFalse(a.any())
                self.assertEqual(a.count(1), 0)
                self.assertEqual(a, bitarray(n * '0'))

            for endian in 'big', 'little':
                a = zeros(3, endian)
                self.assertEqual(a, bitarray('000'))
                self.assertEqual(a.endian(), endian)

    def test_wrong_args(self):
        self.assertRaises(TypeError, zeros) # no argument
        self.assertRaises(TypeError, zeros, '')
        self.assertRaises(TypeError, zeros, bitarray())
        self.assertRaises(TypeError, zeros, [])
        self.assertRaises(TypeError, zeros, 1.0)
        self.assertRaises(ValueError, zeros, -1)

        # endian not string
        for x in 0, 1, {}, [], False, True:
            self.assertRaises(TypeError, zeros, 0, x)
        # endian wrong string
        self.assertRaises(ValueError, zeros, 0, 'foo')

tests.append(TestsZeros)

# ---------------------------------------------------------------------------

class TestsURandom(unittest.TestCase):

    def test_basic(self):
        for default_endian in 'big', 'little':
            _set_default_endian(default_endian)
            a = urandom(0)
            self.assertEqual(a, bitarray())
            self.assertEqual(a.endian(), default_endian)

            a = urandom(7, endian=None)
            self.assertEqual(len(a), 7)
            self.assertEqual(a.endian(), default_endian)

            for n in range(50):
                a = urandom(n)
                self.assertEqual(len(a), n)
                self.assertEqual(a.endian(), default_endian)

            for endian in 'big', 'little':
                a = urandom(11, endian)
                self.assertEqual(len(a), 11)
                self.assertEqual(a.endian(), endian)

    def test_count(self):
        a = urandom(1000)
        b = urandom(1000)
        self.assertNotEqual(a, b)
        self.assertTrue(400 < a.count() < 600)
        self.assertTrue(400 < b.count() < 600)

    def test_wrong_args(self):
        self.assertRaises(TypeError, urandom)
        self.assertRaises(TypeError, urandom, '')
        self.assertRaises(TypeError, urandom, bitarray())
        self.assertRaises(TypeError, urandom, [])
        self.assertRaises(TypeError, urandom, 1.0)
        self.assertRaises(ValueError, urandom, -1)

        self.assertRaises(TypeError, urandom, 0, 1)
        self.assertRaises(ValueError, urandom, 0, 'foo')

tests.append(TestsURandom)

# ---------------------------------------------------------------------------

class TestsPPrint(unittest.TestCase):

    @staticmethod
    def get_code_string(a):
        f = StringIO()
        pprint(a, stream=f)
        return f.getvalue()

    def round_trip(self, a):
        b = eval(self.get_code_string(a))
        self.assertEqual(b, a)
        self.assertEqual(type(b), type(a))

    def test_bitarray(self):
        a = bitarray('110')
        self.assertEqual(self.get_code_string(a), "bitarray('110')\n")
        self.round_trip(a)

    def test_frozenbitarray(self):
        a = frozenbitarray('01')
        self.assertEqual(self.get_code_string(a), "frozenbitarray('01')\n")
        self.round_trip(a)

    def test_formatting(self):
        a = bitarray(200)
        for width in range(40, 130, 10):
            for n in range(1, 10):
                f = StringIO()
                pprint(a, stream=f, group=n, width=width)
                r = f.getvalue()
                self.assertEqual(eval(r), a)
                s = r.strip("bitary(')\n")
                for group in s.split()[:-1]:
                    self.assertEqual(len(group), n)
                for line in s.split('\n'):
                    self.assertTrue(len(line) < width)

    def test_fallback(self):
        for a in None, 'asd', [1, 2], bitarray(), frozenbitarray('1'):
            self.round_trip(a)

    def test_subclass(self):
        class Foo(bitarray):
            pass

        a = Foo()
        code = self.get_code_string(a)
        self.assertEqual(code, "Foo()\n")
        b = eval(code)
        self.assertEqual(b, a)
        self.assertEqual(type(b), type(a))

    def test_random(self):
        for n in range(150):
            self.round_trip(urandom(n))

    def test_file(self):
        tmpdir = tempfile.mkdtemp()
        tmpfile = os.path.join(tmpdir, 'testfile')
        a = bitarray(1000)
        try:
            with open(tmpfile, 'w') as fo:
                pprint(a, fo)
            with open(tmpfile, 'r') as fi:
                b = eval(fi.read())
            self.assertEqual(a, b)
        finally:
            shutil.rmtree(tmpdir)

tests.append(TestsPPrint)

# ---------------------------------------------------------------------------

class TestsMakeEndian(unittest.TestCase, Util):

    def test_simple(self):
        a = bitarray('1110001', endian='big')
        b = make_endian(a, 'big')
        self.assertTrue(b is a)
        c = make_endian(a, endian='little')
        self.assertTrue(c == a)
        self.assertEqual(c.endian(), 'little')
        self.assertIsType(c, 'bitarray')

        # wrong arguments
        self.assertRaises(TypeError, make_endian, '', 'big')
        self.assertRaises(TypeError, make_endian, bitarray(), 1)
        self.assertRaises(ValueError, make_endian, bitarray(), 'foo')

    def test_empty(self):
        a = bitarray(endian='little')
        b = make_endian(a, 'big')
        self.assertTrue(b == a)
        self.assertEqual(len(b), 0)
        self.assertEqual(b.endian(), 'big')

    def test_from_frozen(self):
        a = frozenbitarray('1101111', 'big')
        b = make_endian(a, 'big')
        self.assertTrue(b is a)
        c = make_endian(a, 'little')
        self.assertTrue(c == a)
        self.assertEqual(c.endian(), 'little')
        #self.assertIsType(c, 'frozenbitarray')

    def test_random(self):
        for a in self.randombitarrays():
            aa = a.copy()
            for endian in 'big', 'little':
                b = make_endian(a, endian)
                self.assertEqual(a, b)
                self.assertEqual(b.endian(), endian)
                if a.endian() == endian:
                    self.assertTrue(b is a)
            self.assertEQUAL(a, aa)

tests.append(TestsMakeEndian)

# ---------------------------------------------------------------------------

class TestsRIndex(unittest.TestCase, Util):

    def test_simple(self):
        self.assertRaises(TypeError, rindex)
        self.assertRaises(TypeError, rindex, None)
        self.assertRaises(ValueError, rindex, bitarray(), 1)
        for endian in 'big', 'little':
            a = bitarray('00010110 000', endian)
            self.assertEqual(rindex(a), 6)
            self.assertEqual(rindex(a, 1), 6)
            self.assertEqual(rindex(a, 1, 3), 6)
            self.assertEqual(rindex(a, 1, 3, 8), 6)
            self.assertEqual(rindex(a, 1, -20, 20), 6)
            self.assertEqual(rindex(a, 1, 0, 5), 3)
            self.assertEqual(rindex(a, 1, 0, -6), 3)
            self.assertEqual(rindex(a, 1, 0, -5), 5)
            self.assertRaises(TypeError, rindex, a, 'A')
            self.assertRaises(ValueError, rindex, a, 2)
            self.assertRaises(ValueError, rindex, a, 1, 7)
            self.assertRaises(ValueError, rindex, a, 1, 10, 3)
            self.assertRaises(ValueError, rindex, a, 1, -1, 0)
            self.assertRaises(TypeError, rindex, a, 1, 10, 3, 4)

            a = bitarray('00010110 111', endian)
            self.assertEqual(rindex(a, 0), 7)
            self.assertEqual(rindex(a, 0, 0, 4), 2)
            self.assertEqual(rindex(a, False), 7)

            a = frozenbitarray('00010110 111', endian)
            self.assertEqual(rindex(a, 0), 7)
            self.assertRaises(TypeError, rindex, a, None)
            self.assertRaises(ValueError, rindex, a, 7)

            for v in 0, 1:
                self.assertRaises(ValueError, rindex,
                                  bitarray(0, endian), v)
            self.assertRaises(ValueError, rindex,
                              bitarray('000', endian), 1)
            self.assertRaises(ValueError, rindex,
                              bitarray('11111', endian), 0)

    def test_range(self):
        n = 250
        a = bitarray(n)
        for m in range(n):
            a.setall(0)
            self.assertRaises(ValueError, rindex, a, 1)
            a[m] = 1
            self.assertEqual(rindex(a, 1), m)

            a.setall(1)
            self.assertRaises(ValueError, rindex, a, 0)
            a[m] = 0
            self.assertEqual(rindex(a, 0), m)

    def test_random(self):
        for a in self.randombitarrays():
            v = randint(0, 1)
            try:
                i = rindex(a, v)
            except ValueError:
                i = None
            s = a.to01()
            try:
                j = s.rindex(str(v))
            except ValueError:
                j = None
            self.assertEqual(i, j)

    def test_random_start_stop(self):
        n = 2000
        a = zeros(n)
        indices = [randint(0, n - 1) for _ in range(100)]
        for i in indices:
            a[i] = 1
        for _ in range(100):
            start = randint(0, n)
            stop = randint(0, n)
            filtered = [i for i in indices if i >= start and i < stop]
            ref = max(filtered) if filtered else -1
            try:
                res = rindex(a, 1, start, stop)
            except ValueError:
                res = -1
            self.assertEqual(res, ref)

    def test_many_set(self):
        for _ in range(10):
            n = randint(1, 10000)
            v = randint(0, 1)
            a = bitarray(n)
            a.setall(not v)
            lst = [randint(0, n - 1) for _ in range(100)]
            for i in lst:
                a[i] = v
            self.assertEqual(rindex(a, v), max(lst))

    def test_one_set(self):
        for _ in range(10):
            N = randint(1, 10000)
            a = bitarray(N)
            a.setall(0)
            a[randint(0, N - 1)] = 1
            self.assertEqual(rindex(a), a.index(1))

tests.append(TestsRIndex)

# ---------------------------------------------------------------------------

class TestsStrip(unittest.TestCase, Util):

    def test_simple(self):
        self.assertRaises(TypeError, strip, '0110')
        self.assertRaises(TypeError, strip, bitarray(), 123)
        self.assertRaises(ValueError, strip, bitarray(), 'up')
        for default_endian in 'big', 'little':
            _set_default_endian(default_endian)
            a = bitarray('00010110000')
            self.assertEQUAL(strip(a), bitarray('0001011'))
            self.assertEQUAL(strip(a, 'left'), bitarray('10110000'))
            self.assertEQUAL(strip(a, 'both'), bitarray('1011'))
            b = frozenbitarray('00010110000')
            c = strip(b, 'both')
            self.assertEqual(c, bitarray('1011'))
            self.assertIsType(c, 'frozenbitarray')

    def test_zeros(self):
        for n in range(10):
            for mode in 'left', 'right', 'both':
                a = zeros(n)
                c = strip(a, mode)
                self.assertIsType(c, 'bitarray')
                self.assertEqual(c, bitarray())
                self.assertEqual(a, zeros(n))

                b = frozenbitarray(a)
                c = strip(b, mode)
                self.assertIsType(c, 'frozenbitarray')
                self.assertEqual(c, bitarray())

    def test_random(self):
        for a in self.randombitarrays():
            b = a.copy()
            f = frozenbitarray(a)
            s = a.to01()
            for mode, res in [
                    ('left',  bitarray(s.lstrip('0'), a.endian())),
                    ('right', bitarray(s.rstrip('0'), a.endian())),
                    ('both',  bitarray(s.strip('0'),  a.endian())),
            ]:
                c = strip(a, mode)
                self.assertEQUAL(c, res)
                self.assertIsType(c, 'bitarray')
                self.assertEQUAL(a, b)

                c = strip(f, mode)
                self.assertEQUAL(c, res)
                self.assertIsType(c, 'frozenbitarray')
                self.assertEQUAL(f, b)

    def test_one_set(self):
        for _ in range(10):
            n = randint(1, 10000)
            a = bitarray(n)
            a.setall(0)
            a[randint(0, n - 1)] = 1
            self.assertEqual(strip(a, 'both'), bitarray('1'))
            self.assertEqual(len(a), n)

tests.append(TestsStrip)

# ---------------------------------------------------------------------------

class TestsCount_N(unittest.TestCase, Util):

    @staticmethod
    def count_n(a, n):
        "return lowest index i for which a[:i].count() == n"
        i, j = n, a.count(1, 0, n)
        while j < n:
            j += a[i]
            i += 1
        return i

    def check_result(self, a, n, i, v=1):
        self.assertEqual(a.count(v, 0, i), n)
        if i == 0:
            self.assertEqual(n, 0)
        else:
            self.assertEqual(a[i - 1], v)

    def test_empty(self):
        a = bitarray()
        self.assertEqual(count_n(a, 0), 0)
        self.assertEqual(count_n(a, 0, 0), 0)
        self.assertEqual(count_n(a, 0, 1), 0)
        self.assertRaises(ValueError, count_n, a, 1)
        self.assertRaises(TypeError, count_n, '', 0)
        self.assertRaises(TypeError, count_n, a, 7.0)
        self.assertRaises(ValueError, count_n, a, 0, 2)

    def test_simple(self):
        a = bitarray('111110111110111110111110011110111110111110111000')
        b = a.copy()
        self.assertEqual(len(a), 48)
        self.assertEqual(a.count(), 37)
        self.assertEqual(a.count(0), 11)

        self.assertEqual(count_n(a, 0, 0), 0)
        self.assertEqual(count_n(a, 2, 0), 12)
        self.assertEqual(count_n(a, 10, 0), 47)
        self.assertRaisesMessage(ValueError, "non-negative integer expected",
                                 count_n, a, -1, 0) # n < 0
        self.assertRaisesMessage(ValueError, "n larger than bitarray size",
                                 count_n, a, 49, 0) # n > len(a)
        self.assertRaisesMessage(ValueError, "n exceeds total count",
                                 count_n, a, 12, 0) # n > a.count(0)

        self.assertEqual(count_n(a, 0), 0)
        self.assertEqual(count_n(a, 20), 23)
        self.assertEqual(count_n(a, 20, 1), 23)
        self.assertEqual(count_n(a, 37), 45)
        self.assertRaisesMessage(ValueError, "non-negative integer expected",
                                 count_n, a, -1) # n < 0
        self.assertRaisesMessage(ValueError, "n larger than bitarray size",
                                 count_n, a, 49) # n > len(a)
        self.assertRaisesMessage(ValueError, "n exceeds total count",
                                 count_n, a, 38) # n > a.count()

        for v in 0, 1:
            for n in range(a.count(v) + 1):
                i = count_n(a, n, v)
                self.check_result(a, n, i, v)
                self.assertEqual(a[:i].count(v), n)
                self.assertEqual(i, self.count_n(a if v else ~a, n))
        self.assertEQUAL(a, b)

    def test_frozen(self):
        a = frozenbitarray('001111101111101111101111100111100')
        self.assertEqual(len(a), 33)
        self.assertEqual(a.count(), 24)
        self.assertEqual(count_n(a, 0), 0)
        self.assertEqual(count_n(a, 10), 13)
        self.assertEqual(count_n(a, 24), 31)
        self.assertRaises(ValueError, count_n, a, -1) # n < 0
        self.assertRaises(ValueError, count_n, a, 25) # n > a.count()
        self.assertRaises(ValueError, count_n, a, 34) # n > len(a)
        for n in range(25):
            self.check_result(a, n, count_n(a, n))

    def test_ones(self):
        n = randint(1, 100000)
        a = bitarray(n)
        a.setall(1)
        self.assertEqual(count_n(a, n), n)
        self.assertRaises(ValueError, count_n, a, 1, 0)
        self.assertRaises(ValueError, count_n, a, n + 1)
        for _ in range(20):
            i = randint(0, n)
            self.assertEqual(count_n(a, i), i)

    def test_one_set(self):
        n = randint(1, 100000)
        a = bitarray(n)
        a.setall(0)
        self.assertEqual(count_n(a, 0), 0)
        self.assertRaises(ValueError, count_n, a, 1)
        for _ in range(20):
            a.setall(0)
            i = randint(0, n - 1)
            a[i] = 1
            self.assertEqual(count_n(a, 1), i + 1)
            self.assertRaises(ValueError, count_n, a, 2)

    def test_large(self):
        for _ in range(100):
            N = randint(100000, 250000)
            a = bitarray(N)
            v = randint(0, 1)
            a.setall(not v)
            for _ in range(randint(0, 100)):
                a[randint(0, N - 1)] = v
            tc = a.count(v)      # total count
            i = count_n(a, tc, v)
            self.check_result(a, tc, i, v)
            self.assertRaises(ValueError, count_n, a, tc + 1, v)
            for _ in range(20):
                n = randint(0, tc)
                i = count_n(a, n, v)
                self.check_result(a, n, i, v)

    def test_random(self):
        for a in self.randombitarrays():
            for v in 0, 1:
                n = a.count(v) // 2
                i = count_n(a, n, v)
                self.check_result(a, n, i, v)

tests.append(TestsCount_N)

# ---------------------------------------------------------------------------

class TestsBitwiseCount(unittest.TestCase, Util):

    def test_count_byte(self):
        ones = bitarray(8)
        ones.setall(1)
        zeros = bitarray(8)
        zeros.setall(0)
        for i in range(256):
            a = bitarray()
            a.frombytes(bytes(bytearray([i])))
            cnt = a.count()
            self.assertEqual(count_and(a, zeros), 0)
            self.assertEqual(count_and(a, ones), cnt)
            self.assertEqual(count_and(a, a), cnt)
            self.assertEqual(count_or(a, zeros), cnt)
            self.assertEqual(count_or(a, ones), 8)
            self.assertEqual(count_or(a, a), cnt)
            self.assertEqual(count_xor(a, zeros), cnt)
            self.assertEqual(count_xor(a, ones), 8 - cnt)
            self.assertEqual(count_xor(a, a), 0)

    def test_bit_count1(self):
        a = bitarray('001111')
        aa = a.copy()
        b = bitarray('010011')
        bb = b.copy()
        self.assertEqual(count_and(a, b), 2)
        self.assertEqual(count_or(a, b), 5)
        self.assertEqual(count_xor(a, b), 3)
        for f in count_and, count_or, count_xor:
            # not two arguments
            self.assertRaises(TypeError, f)
            self.assertRaises(TypeError, f, a)
            self.assertRaises(TypeError, f, a, b, 3)
            # wrong argument types
            self.assertRaises(TypeError, f, a, '')
            self.assertRaises(TypeError, f, '1', b)
            self.assertRaises(TypeError, f, a, 4)
        self.assertEQUAL(a, aa)
        self.assertEQUAL(b, bb)

        b.append(1)
        for f in count_and, count_or, count_xor:
            self.assertRaises(ValueError, f, a, b)
            self.assertRaises(ValueError, f,
                              bitarray('110', 'big'),
                              bitarray('101', 'little'))

    def test_bit_count_frozen(self):
        a = frozenbitarray('001111')
        b = frozenbitarray('010011')
        self.assertEqual(count_and(a, b), 2)
        self.assertEqual(count_or(a, b), 5)
        self.assertEqual(count_xor(a, b), 3)

    def test_bit_count_random(self):
        for n in list(range(50)) + [randint(1000, 2000)]:
            a = urandom(n)
            b = urandom(n)
            self.assertEqual(count_and(a, b), (a & b).count())
            self.assertEqual(count_or(a, b),  (a | b).count())
            self.assertEqual(count_xor(a, b), (a ^ b).count())

tests.append(TestsBitwiseCount)

# ---------------------------------------------------------------------------

class TestsSubset(unittest.TestCase, Util):

    def test_basic(self):
        a = frozenbitarray('0101')
        b = bitarray('0111')
        self.assertTrue(subset(a, b))
        self.assertFalse(subset(b, a))
        self.assertRaises(TypeError, subset)
        self.assertRaises(TypeError, subset, a, '')
        self.assertRaises(TypeError, subset, '1', b)
        self.assertRaises(TypeError, subset, a, 4)
        b.append(1)
        self.assertRaises(ValueError, subset, a, b)
        self.assertRaises(ValueError, subset,
                          bitarray('01', 'little'),
                          bitarray('11', 'big'))

    def check(self, a, b, res):
        r = subset(a, b)
        self.assertIsInstance(r, bool)
        self.assertEqual(r, res)
        self.assertEqual(a | b == b, res)
        self.assertEqual(a & b == a, res)

    def test_True(self):
        for a, b in [('', ''), ('0', '1'), ('0', '0'), ('1', '1'),
                     ('000', '111'), ('0101', '0111'),
                     ('000010111', '010011111')]:
            self.check(bitarray(a), bitarray(b), True)

    def test_False(self):
        for a, b in [('1', '0'), ('1101', '0111'),
                     ('0000101111', '0100111011')]:
            self.check(bitarray(a), bitarray(b), False)

    def test_random(self):
        for a in self.randombitarrays(start=1):
            b = a.copy()
            # we set one random bit in b to 1, so a is always a subset of b
            b[randint(0, len(a) - 1)] == 1
            self.check(a, b, True)
            # but b is only a subset when they are equal
            self.check(b, a, a == b)
            # we set all bits in a, which ensures that b is a subset of a
            a.setall(1)
            self.check(b, a, True)

tests.append(TestsSubset)

# ---------------------------------------------------------------------------

class TestsParity(unittest.TestCase, Util):

    def test_bitarray(self):
        a = bitarray()
        self.assertBitEqual(parity(a), 0)
        par = False
        for _ in range(100):
            self.assertEqual(parity(a), par)
            a.append(1)
            par = not par

    def test_unused_bits(self):
        a = bitarray(1)
        a.setall(1)
        self.assertTrue(parity(a))

    def test_frozenbitarray(self):
        self.assertBitEqual(parity(frozenbitarray()), 0)
        self.assertBitEqual(parity(frozenbitarray('0010011')), 1)
        self.assertBitEqual(parity(frozenbitarray('10100110')), 0)

    def test_wrong_args(self):
        self.assertRaises(TypeError, parity, '')
        self.assertRaises(TypeError, bitarray(), 1)

    def test_byte(self):
        for i in range(256):
            a = bitarray()
            a.frombytes(bytes(bytearray([i])))
            self.assertEqual(parity(a), a.count() % 2)

    def test_random(self):
        for a in self.randombitarrays():
            self.assertEqual(parity(a), a.count() % 2)

tests.append(TestsParity)

# ---------------------------------------------------------------------------

class TestsHexlify(unittest.TestCase, Util):

    def test_ba2hex(self):
        self.assertEqual(ba2hex(bitarray(0, 'big')), '')
        self.assertEqual(ba2hex(bitarray('1110', 'big')), 'e')
        self.assertEqual(ba2hex(bitarray('1110', 'little')), '7')
        self.assertEqual(ba2hex(bitarray('0000 0001', 'big')), '01')
        self.assertEqual(ba2hex(bitarray('1000 0000', 'big')), '80')
        self.assertEqual(ba2hex(bitarray('0000 0001', 'little')), '08')
        self.assertEqual(ba2hex(bitarray('1000 0000', 'little')), '10')
        self.assertEqual(ba2hex(frozenbitarray('1100 0111', 'big')), 'c7')
        # length not multiple of 4
        self.assertRaises(ValueError, ba2hex, bitarray('10'))
        self.assertRaises(TypeError, ba2hex, '101')

        c = ba2hex(bitarray('1101', 'big'))
        self.assertIsInstance(c, str)

        for n in range(7):
            a = bitarray(n * '1111', 'big')
            b = a.copy()
            self.assertEqual(ba2hex(a), n * 'f')
            # ensure original object wasn't altered
            self.assertEQUAL(a, b)

    def test_hex2ba(self):
        _set_default_endian('big')
        self.assertEqual(hex2ba(''), bitarray())
        for c in 'e', 'E', b'e', b'E', u'e', u'E':
            a = hex2ba(c)
            self.assertEqual(a.to01(), '1110')
            self.assertEqual(a.endian(), 'big')
        self.assertEQUAL(hex2ba('01'), bitarray('0000 0001', 'big'))
        self.assertEQUAL(hex2ba('08', 'little'),
                         bitarray('0000 0001', 'little'))
        self.assertEQUAL(hex2ba('aD'), bitarray('1010 1101', 'big'))
        self.assertEQUAL(hex2ba(b'10aF'),
                         bitarray('0001 0000 1010 1111', 'big'))
        self.assertEQUAL(hex2ba(b'10aF', 'little'),
                         bitarray('1000 0000 0101 1111', 'little'))

    def test_hex2ba_errors(self):
        self.assertRaises(TypeError, hex2ba, 0)

        for endian in 'little', 'big':
            _set_default_endian(endian)
            self.assertRaises(ValueError, hex2ba, '01a7g89')
            self.assertRaises(UnicodeEncodeError, hex2ba, u'10\u20ac')
            # check for NUL bytes
            for b in b'\0', b'\0f', b'f\0', b'\0ff', b'f\0f', b'ff\0':
                self.assertRaises(ValueError, hex2ba, b)

    def test_explicit(self):
        data = [ #                       little   big
            ('',                         '',      ''),
            ('1000',                     '1',     '8'),
            ('1000 1100',                '13',    '8c'),
            ('1000 1100 1110',           '137',   '8ce'),
            ('1000 1100 1110 1111' ,     '137f',  '8cef'),
            ('1000 1100 1110 1111 0100', '137f2', '8cef4'),
        ]
        for bs, hex_le, hex_be in data:
            a_be = bitarray(bs, 'big')
            a_le = bitarray(bs, 'little')
            self.assertEQUAL(hex2ba(hex_be, 'big'), a_be)
            self.assertEQUAL(hex2ba(hex_le, 'little'), a_le)
            self.assertEqual(ba2hex(a_be), hex_be)
            self.assertEqual(ba2hex(a_le), hex_le)

    def test_round_trip(self):
        s = ''.join(choice(hexdigits) for _ in range(randint(20, 100)))
        for default_endian in 'big', 'little':
            _set_default_endian(default_endian)
            a = hex2ba(s)
            self.check_obj(a)
            self.assertEqual(len(a) % 4, 0)
            self.assertEqual(a.endian(), default_endian)
            t = ba2hex(a)
            self.assertEqual(t, s.lower())
            b = hex2ba(t, default_endian)
            self.assertEQUAL(a, b)

    def test_binascii(self):
        a = urandom(800, 'big')
        s = binascii.hexlify(a.tobytes()).decode()
        self.assertEqual(ba2hex(a), s)
        b = bitarray(endian='big')
        b.frombytes(binascii.unhexlify(s))
        self.assertEQUAL(hex2ba(s, 'big'), b)

tests.append(TestsHexlify)

# ---------------------------------------------------------------------------

class TestsBase(unittest.TestCase, Util):

    def test_ba2base(self):
        c = ba2base(16, bitarray('1101', 'big'))
        self.assertIsInstance(c, str)

    def test_base2ba(self):
        _set_default_endian('big')
        for c in 'e', 'E', b'e', b'E', u'e', u'E':
            a = base2ba(16, c)
            self.assertEqual(a.to01(), '1110')
            self.assertEqual(a.endian(), 'big')

    def test_explicit(self):
        data = [ #              n  little   big
            ('',                2, '',      ''),
            ('1 0 1',           2, '101',   '101'),
            ('11 01 00',        4, '320',   '310'),
            ('111 001',         8, '74',    '71'),
            ('1111 0001',      16, 'f8',    'f1'),
            ('11111 00001',    32, '7Q',    '7B'),
            ('111111 000001',  64, '/g',    '/B'),
        ]
        for bs, n, s_le, s_be in data:
            a_le = bitarray(bs, 'little')
            a_be = bitarray(bs, 'big')
            self.assertEQUAL(base2ba(n, s_le, 'little'), a_le)
            self.assertEQUAL(base2ba(n, s_be, 'big'),    a_be)
            self.assertEqual(ba2base(n, a_le), s_le)
            self.assertEqual(ba2base(n, a_be), s_be)

    def test_empty(self):
        for n in 2, 4, 8, 16, 32, 64:
            a = base2ba(n, '')
            self.assertEqual(a, bitarray())
            self.assertEqual(ba2base(n, a), '')

    def test_upper(self):
        self.assertEqual(base2ba(16, 'F'), bitarray('1111'))

    def test_invalid_characters(self):
        for n, s in ((2, '2'), (4, '4'), (8, '8'), (16, 'g'), (32, '8'),
                     (32, '1'), (32, 'a'), (64, '-'), (64, '_')):
            self.assertRaises(ValueError, base2ba, n, s)

    def test_invalid_args(self):
        a = bitarray()
        self.assertRaises(TypeError, ba2base, None, a)
        self.assertRaises(TypeError, base2ba, None, '')
        self.assertRaises(TypeError, ba2base, 16.0, a)
        self.assertRaises(TypeError, base2ba, 16.0, '')
        for i in range(-10, 260):
            if i in (2, 4, 8, 16, 32, 64):
                continue
            self.assertRaises(ValueError, ba2base, i, a)
            self.assertRaises(ValueError, base2ba, i, '')

        self.assertRaises(TypeError, ba2base, 32, None)
        self.assertRaises(TypeError, base2ba, 32, None)

    def test_binary(self):
        a = base2ba(2, '1011')
        self.assertEqual(a, bitarray('1011'))
        self.assertEqual(ba2base(2, a), '1011')

        for a in self.randombitarrays():
            s = ba2base(2, a)
            self.assertEqual(s, a.to01())
            self.assertEQUAL(base2ba(2, s, a.endian()), a)

    def test_quaternary(self):
        a = base2ba(4, '0123', 'big')
        self.assertEqual(a, bitarray('00 01 10 11'))
        self.assertEqual(ba2base(4, a), '0123')

    def test_octal(self):
        a = base2ba(8, '0147', 'big')
        self.assertEqual(a, bitarray('000 001 100 111'))
        self.assertEqual(ba2base(8, a), '0147')

    def test_hexadecimal(self):
        a = base2ba(16, 'F61', 'big')
        self.assertEqual(a, bitarray('1111 0110 0001'))
        self.assertEqual(ba2base(16, a), 'f61')

        for n in range(50):
            s = ''.join(choice(hexdigits) for _ in range(n))
            for endian in 'big', 'little':
                a = base2ba(16, s, endian)
                self.assertEQUAL(a, hex2ba(s, endian))
                self.assertEqual(ba2base(16, a), ba2hex(a))

    def test_base32(self):
        a = base2ba(32, '7SH', 'big')
        self.assertEqual(a, bitarray('11111 10010 00111'))
        self.assertEqual(ba2base(32, a), '7SH')

        msg = os.urandom(randint(10, 100) * 5)
        s = base64.b32encode(msg).decode()
        a = base2ba(32, s, 'big')
        self.assertEqual(a.tobytes(), msg)
        self.assertEqual(ba2base(32, a), s)

    def test_base64(self):
        a = base2ba(64, '/jH', 'big')
        self.assertEqual(a, bitarray('111111 100011 000111'))
        self.assertEqual(ba2base(64, a), '/jH')

        msg = os.urandom(randint(10, 100) * 3)
        s = base64.standard_b64encode(msg).decode()
        a = base2ba(64, s, 'big')
        self.assertEqual(a.tobytes(), msg)
        self.assertEqual(ba2base(64, a), s)

    def test_alphabets(self):
        for m, n, alpabet in [
                (1,  2, '01'),
                (2,  4, '0123'),
                (3,  8, '01234567'),
                (4, 16, '0123456789abcdef'),
                (5, 32, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'),
                (6, 64, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                        'abcdefghijklmnopqrstuvwxyz0123456789+/'),
        ]:
            self.assertEqual(1 << m, n)
            self.assertEqual(len(alpabet), n)
            for i, c in enumerate(alpabet):
                for endian in 'big', 'little':
                    self.assertEqual(ba2int(base2ba(n, c, endian)), i)
                    self.assertEqual(ba2base(n, int2ba(i, m, endian)), c)

    def test_random(self):
        for a in self.randombitarrays():
            for m in range(1, 7):
                n = 1 << m
                if len(a) % m == 0:
                    s = ba2base(n, a)
                    b = base2ba(n, s, a.endian())
                    self.assertEQUAL(a, b)
                    self.check_obj(b)
                else:
                    self.assertRaises(ValueError, ba2base, n, a)

    def test_random2(self):
        for m in range(1, 7):
            n = 1 << m
            for length in range(0, 100, m):
                a = urandom(length, 'little')
                self.assertEQUAL(base2ba(n, ba2base(n, a), 'little'), a)
                b = bitarray(a, 'big')
                self.assertEQUAL(base2ba(n, ba2base(n, b), 'big'), b)

tests.append(TestsBase)

# ---------------------------------------------------------------------------

class VLFTests(unittest.TestCase, Util):

    def test_explicit(self):
        for s, bits in [
                (b'\x40', ''),
                (b'\x30', '0'),
                (b'\x38', '1'),
                (b'\x00', '0000'),
                (b'\x01', '0001'),
                (b'\xe0\x40', '0000 1'),
                (b'\x90\x02', '0000 000001'),
                (b'\xb5\xa7\x18', '0101 0100111 0011'),
        ]:
            a = bitarray(bits)
            self.assertEqual(vl_encode(a), s)
            self.assertEqual(vl_decode(s), a)

    def test_encode(self):
        for endian in 'big', 'little':
            s = vl_encode(bitarray('001101', endian))
            self.assertIsInstance(s, bytes)
            self.assertEqual(s, b'\xd3\x20')

    def test_decode_args(self):
        if sys.version_info[0] == 3:
            self.assertRaises(TypeError, vl_decode, 'foo')
            # item not integer
            self.assertRaises(TypeError, vl_decode, iter([b'\x40']))

        self.assertRaises(TypeError, vl_decode, b'\x40', 'big', 3)
        self.assertRaises(ValueError, vl_decode, b'\x40', 'foo')
        # these objects are not iterable
        for arg in None, 0, 1, 0.0:
            self.assertRaises(TypeError, vl_decode, arg)
        # these items cannot be interpreted as ints
        for item in None, 2.34, Ellipsis:
            self.assertRaises(TypeError, vl_decode, iter([0x95, item]))

        b = b'\xd3\x20'
        lst = [b, iter(b), memoryview(b)]
        if sys.version_info[0] == 3:
            lst.append(iter([0xd3, 0x20]))
            lst.append(bytearray(b))
        for s in lst:
            a = vl_decode(s, endian=self.random_endian())
            self.assertIsInstance(a, bitarray)
            self.assertEqual(a, bitarray('0011 01'))

    def test_decode_endian(self):
        for endian in 'little', 'big', None:
            a = vl_decode(b'\xd3\x20', endian)
            self.assertEqual(a, bitarray('0011 01'))
            self.assertEqual(a.endian(),
                             endian if endian else get_default_endian())

    def test_decode_trailing(self):
        for s, bits in [(b'\x40ABC', ''),
                        (b'\xe0\x40A', '00001')]:
            stream = iter(s)
            self.assertEqual(vl_decode(stream), bitarray(bits))
            self.assertEqual(next(stream),
                             b'A' if sys.version_info[0] == 2 else 65)

    def test_decode_ambiguity(self):
        for s in b'\x40', b'\x4f', b'\x45':
            self.assertEqual(vl_decode(iter(s)), bitarray())
        for s in b'\x1e', b'\x1f':
            self.assertEqual(vl_decode(iter(s)), bitarray('111'))

    def test_decode_stream(self):
        stream = iter(b'\x40\x30\x38\x40\x2c\xe0\x40\xd3\x20')
        for bits in '', '0', '1', '', '11', '0000 1', '0011 01':
            self.assertEqual(vl_decode(stream), bitarray(bits))

        arrays = [urandom(randint(0, 30)) for _ in range(1000)]
        stream = iter(b''.join(vl_encode(a) for a in arrays))
        for a in arrays:
            self.assertEqual(vl_decode(stream), a)

    def test_decode_errors(self):
        # decode empty bits
        self.assertRaises(StopIteration, vl_decode, b'')
        # invalid number of padding bits
        for s in b'\x50', b'\x60', b'\x70':
            self.assertRaises(ValueError, vl_decode, s)
        self.assertRaises(ValueError, vl_decode, b'\xf0')
        # high bit set, but no terminating byte
        for s in b'\x80', b'\x80\x80':
            self.assertRaises(StopIteration, vl_decode, s)

    def test_decode_error_message(self):
        pat = re.compile(r'[\w\s,]+:\s+(\d+)')
        for n in range(120):
            a = None
            s = bytes(bytearray([randint(0x80, 0xef) for _ in range(n)]))
            try:
                a = vl_decode(s)
            except StopIteration as e:
                m = pat.match(str(e))
                self.assertEqual(m.group(1), str(n))
            self.assertTrue(a is None)

    @skipIf(sys.version_info[0] == 2)
    def test_decode_invalid_stream(self):
        N = 100
        s = iter(N * (3 * [0x80] + ['XX']) + ['end.'])
        for _ in range(N):
            a = None
            try:
                a = vl_decode(s)
            except TypeError:
                pass
            self.assertTrue(a is None)
        self.assertEqual(next(s), 'end.')

    def test_explicit_zeros(self):
        for n in range(100):
            a = zeros(4 + n * 7)
            s = n * b'\x80' + b'\x00'
            self.assertEqual(vl_encode(a), s)
            self.assertEqual(vl_decode(s), a)

    def round_trip(self, a):
        s = vl_encode(a)
        b = vl_decode(s)
        self.check_obj(b)
        self.assertEqual(a, b)
        LEN_PAD_BITS = 3
        self.assertEqual(len(s), (len(a) + LEN_PAD_BITS + 6) // 7)

        head = ord(s[0]) if sys.version_info[0] == 2 else s[0]
        padding = (head & 0x70) >> 4
        self.assertEqual(len(a) + padding, 7 * len(s) - LEN_PAD_BITS)

    def test_range(self):
        for n in range(500):
            self.round_trip(urandom(n))

    def test_large(self):
        a = urandom(randint(50000, 100000))
        self.round_trip(a)

    def test_random(self):
        for a in self.randombitarrays():
            self.round_trip(a)

tests.append(VLFTests)

# ---------------------------------------------------------------------------

class TestsIntegerization(unittest.TestCase, Util):

    def test_ba2int(self):
        self.assertEqual(ba2int(bitarray('0')), 0)
        self.assertEqual(ba2int(bitarray('1')), 1)
        self.assertEqual(ba2int(bitarray('00101', 'big')), 5)
        self.assertEqual(ba2int(bitarray('00101', 'little')), 20)
        self.assertEqual(ba2int(frozenbitarray('11')), 3)
        self.assertRaises(ValueError, ba2int, bitarray())
        self.assertRaises(ValueError, ba2int, frozenbitarray())
        self.assertRaises(TypeError, ba2int, '101')
        a = bitarray('111')
        b = a.copy()
        self.assertEqual(ba2int(a), 7)
        # ensure original object wasn't altered
        self.assertEQUAL(a, b)

    def test_ba2int_frozen(self):
        for a in self.randombitarrays(start=1):
            b = frozenbitarray(a)
            self.assertEqual(ba2int(b), ba2int(a))
            self.assertEQUAL(a, b)

    def test_ba2int_random(self):
        for a in self.randombitarrays(start=1):
            b = bitarray(a, 'big')
            self.assertEqual(a, b)
            self.assertEqual(ba2int(b), int(b.to01(), 2))

    def test_ba2int_bytes(self):
        for n in range(1, 50):
            a = urandom(8 * n, self.random_endian())
            c = bytearray(a.tobytes())
            i = 0
            for x in (c if a.endian() == 'big' else reversed(c)):
                i <<= 8
                i |= x
            self.assertEqual(ba2int(a), i)

    def test_int2ba(self):
        self.assertEqual(int2ba(0), bitarray('0'))
        self.assertEqual(int2ba(1), bitarray('1'))
        self.assertEqual(int2ba(5), bitarray('101'))
        self.assertEQUAL(int2ba(6, endian='big'), bitarray('110', 'big'))
        self.assertEQUAL(int2ba(6, endian='little'),
                         bitarray('011', 'little'))
        self.assertRaises(TypeError, int2ba, 1.0)
        self.assertRaises(TypeError, int2ba, 1, 3.0)
        self.assertRaises(ValueError, int2ba, 1, 0)
        self.assertRaises(TypeError, int2ba, 1, 10, 123)
        self.assertRaises(ValueError, int2ba, 1, 10, 'asd')
        # signed integer requires length
        self.assertRaises(TypeError, int2ba, 100, signed=True)

    def test_signed(self):
        for s, i in [
                ('0',  0),
                ('1', -1),
                ('00',  0),
                ('10',  1),
                ('01', -2),
                ('11', -1),
                ('000',  0),
                ('100',  1),
                ('010',  2),
                ('110',  3),
                ('001', -4),
                ('101', -3),
                ('011', -2),
                ('111', -1),
                ('00000',   0),
                ('11110',  15),
                ('00001', -16),
                ('11111',  -1),
                ('00000000 0',    0),
                ('11111111 0',  255),
                ('00000000 1', -256),
                ('11111111 1',   -1),
                ('00000000 00000000 000000', 0),
                ('10010000 11000000 100010', 9 + 3 * 256 + 17 * 2 ** 16),
                ('11111111 11111111 111110', 2 ** 21 - 1),
                ('00000000 00000000 000001', -2 ** 21),
                ('10010000 11000000 100011', -2 ** 21
                                           + (9 + 3 * 256 + 17 * 2 ** 16)),
                ('11111111 11111111 111111', -1),
        ]:
            self.assertEqual(ba2int(bitarray(s, 'little'), signed=1), i)
            self.assertEqual(ba2int(bitarray(s[::-1], 'big'), signed=1), i)

            len_s = len(bitarray(s))
            self.assertEQUAL(int2ba(i, len_s, 'little', signed=1),
                             bitarray(s, 'little'))
            self.assertEQUAL(int2ba(i, len_s, 'big', signed=1),
                             bitarray(s[::-1], 'big'))

    def test_int2ba_overflow(self):
        self.assertRaises(OverflowError, int2ba, -1)
        self.assertRaises(OverflowError, int2ba, -1, 4)

        self.assertRaises(OverflowError, int2ba, 128, 7)
        self.assertRaises(OverflowError, int2ba, 64, 7, signed=1)
        self.assertRaises(OverflowError, int2ba, -65, 7, signed=1)

        for n in range(1, 20):
            self.assertRaises(OverflowError, int2ba, 2 ** n, n)
            self.assertRaises(OverflowError, int2ba, 2 ** (n - 1), n,
                              signed=1)
            self.assertRaises(OverflowError, int2ba, -2 ** (n - 1) - 1, n,
                              signed=1)

    def test_int2ba_length(self):
        self.assertRaises(TypeError, int2ba, 0, 1.0)
        self.assertRaises(ValueError, int2ba, 0, 0)
        self.assertEqual(int2ba(5, length=6, endian='big'),
                         bitarray('000101'))
        for n in range(1, 100):
            ab = int2ba(1, n, 'big')
            al = int2ba(1, n, 'little')
            self.assertEqual(ab.endian(), 'big')
            self.assertEqual(al.endian(), 'little')
            self.assertEqual(len(ab), n),
            self.assertEqual(len(al), n)
            self.assertEqual(ab, bitarray((n - 1) * '0') + bitarray('1'))
            self.assertEqual(al, bitarray('1') + bitarray((n - 1) * '0'))

            ab = int2ba(0, n, 'big')
            al = int2ba(0, n, 'little')
            self.assertEqual(len(ab), n)
            self.assertEqual(len(al), n)
            self.assertEqual(ab, bitarray(n * '0', 'big'))
            self.assertEqual(al, bitarray(n * '0', 'little'))

            self.assertEqual(int2ba(2 ** n - 1), bitarray(n * '1'))
            self.assertEqual(int2ba(2 ** n - 1, endian='little'),
                             bitarray(n * '1'))
            for endian in 'big', 'little':
                self.assertEqual(int2ba(-1, n, endian, signed=True),
                                 bitarray(n * '1'))

    def test_explicit(self):
        _set_default_endian('big')
        for i, sa in [( 0,     '0'),    (1,         '1'),
                      ( 2,    '10'),    (3,        '11'),
                      (25, '11001'),  (265, '100001001'),
                      (3691038, '1110000101001000011110')]:
            ab = bitarray(sa, 'big')
            al = bitarray(sa[::-1], 'little')
            self.assertEQUAL(int2ba(i), ab)
            self.assertEQUAL(int2ba(i, endian='big'), ab)
            self.assertEQUAL(int2ba(i, endian='little'), al)
            self.assertEqual(ba2int(ab), ba2int(al), i)

    def check_round_trip(self, i):
        for endian in 'big', 'little':
            a = int2ba(i, endian=endian)
            self.check_obj(a)
            self.assertEqual(a.endian(), endian)
            self.assertTrue(len(a) > 0)
            # ensure we have no leading zeros
            if a.endian == 'big':
                self.assertTrue(len(a) == 1 or a.index(1) == 0)
            self.assertEqual(ba2int(a), i)
            if i > 0:
                self.assertEqual(i.bit_length(), len(a))
            # add a few trailing / leading zeros to bitarray
            if endian == 'big':
                a = zeros(randint(0, 3), endian) + a
            else:
                a = a + zeros(randint(0, 3), endian)
            self.assertEqual(a.endian(), endian)
            self.assertEqual(ba2int(a), i)

    def test_many(self):
        for i in range(20):
            self.check_round_trip(i)
            self.check_round_trip(randint(0, 10 ** randint(3, 300)))

    @staticmethod
    def twos_complement(i, num_bits):
        # https://en.wikipedia.org/wiki/Two%27s_complement
        mask = 2 ** (num_bits - 1)
        return -(i & mask) + (i & ~mask)

    def test_random_signed(self):
        for a in self.randombitarrays(start=1):
            i = ba2int(a, signed=True)
            b = int2ba(i, len(a), a.endian(), signed=True)
            self.assertEQUAL(a, b)

            j = ba2int(a, signed=False)  # unsigned
            if i >= 0:
                self.assertEqual(i, j)

            self.assertEqual(i, self.twos_complement(j, len(a)))

tests.append(TestsIntegerization)

# ---------------------------------------------------------------------------

class MixedTests(unittest.TestCase, Util):

    def test_bin(self):
        for i in range(100):
            s = bin(i)
            self.assertEqual(s[:2], '0b')
            a = bitarray(s[2:], 'big')
            self.assertEqual(ba2int(a), i)
            t = '0b%s' % a.to01()
            self.assertEqual(t, s)
            self.assertEqual(eval(t), i)

    @skipIf(sys.version_info[0] == 2)
    def test_oct(self):
        for i in range(1000):
            s = oct(i)
            self.assertEqual(s[:2], '0o')
            a = base2ba(8, s[2:], 'big')
            self.assertEqual(ba2int(a), i)
            t = '0o%s' % ba2base(8, a)
            self.assertEqual(t, s)
            self.assertEqual(eval(t), i)

    def test_hex(self):
        for i in range(1000):
            s = hex(i)
            self.assertEqual(s[:2], '0x')
            a = hex2ba(s[2:], 'big')
            self.assertEqual(ba2int(a), i)
            t = '0x%s' % ba2hex(a)
            self.assertEqual(t, s)
            self.assertEqual(eval(t), i)

    def test_bitwise(self):
        for a in self.randombitarrays(start=1):
            b = urandom(len(a), a.endian())
            aa = a.copy()
            bb = b.copy()
            i = ba2int(a)
            j = ba2int(b)
            self.assertEqual(ba2int(a & b), i & j)
            self.assertEqual(ba2int(a | b), i | j)
            self.assertEqual(ba2int(a ^ b), i ^ j)

            n = randint(0, len(a))
            if a.endian() == 'big':
                self.assertEqual(ba2int(a >> n), i >> n)
                c = zeros(len(a), 'big') + a
                self.assertEqual(ba2int(c << n), i << n)

            self.assertEQUAL(a, aa)
            self.assertEQUAL(b, bb)

    def test_bitwise_inplace(self):
        for a in self.randombitarrays(start=1):
            b = urandom(len(a), a.endian())
            bb = b.copy()
            i = ba2int(a)
            j = ba2int(b)
            c = a.copy()
            c &= b
            self.assertEqual(ba2int(c), i & j)
            c = a.copy()
            c |= b
            self.assertEqual(ba2int(c), i | j)
            c = a.copy()
            c ^= b
            self.assertEqual(ba2int(c), i ^ j)
            self.assertEQUAL(b, bb)

            n = randint(0, len(a))
            if a.endian() == 'big':
                c = a.copy()
                c >>= n
                self.assertEqual(ba2int(c), i >> n)
                c = zeros(len(a), 'big') + a
                c <<= n
                self.assertEqual(ba2int(c), i << n)

    def test_primes(self):  # Sieve of Eratosthenes
        sieve = bitarray(10000)
        sieve.setall(1)
        sieve[:2] = 0  # zero and one are not prime
        for i in range(2, 100):
            if sieve[i]:
                sieve[i * i::i] = 0
        # the first 15 primes
        self.assertEqual(sieve.search(1, 15), [2, 3, 5, 7, 11, 13, 17, 19,
                                               23, 29, 31, 37, 41, 43, 47])
        # there are 1229 primes between 1 and 10000
        self.assertEqual(sieve.count(1), 1229)
        # there are 119 primes between 4000 and 5000
        self.assertEqual(sieve.count(1, 4000, 5000), 119)
        # the 1000th prime is 7919
        self.assertEqual(count_n(sieve, 1000) - 1, 7919)

tests.append(MixedTests)

# ---------------------------------------------------------------------------

class TestsSerialization(unittest.TestCase, Util):

    def test_explicit(self):
        for a, b in [
                (bitarray(0, 'little'),   b'\x00'),
                (bitarray(0, 'big'),      b'\x10'),
                (bitarray('1', 'little'), b'\x07\x01'),
                (bitarray('1', 'big'),    b'\x17\x80'),
                (bitarray('11110000', 'little'), b'\x00\x0f'),
                (bitarray('11110000', 'big'),    b'\x10\xf0'),
        ]:
            self.assertEqual(serialize(a), b)
            self.assertEQUAL(deserialize(b), a)

    def test_zeros_and_ones(self):
        for endian in 'little', 'big':
            for n in range(50):
                a = zeros(n, endian)
                s = serialize(a)
                self.assertIsInstance(s, bytes)
                self.assertEqual(s[1:], b'\0' * a.nbytes)
                self.assertEQUAL(a, deserialize(s))
                a.setall(1)
                self.assertEQUAL(a, deserialize(serialize(a)))

    def test_serialize_args(self):
        for x in '0', 0, 1, b'\x00', 0.0, [0, 1], bytearray([0]):
            self.assertRaises(TypeError, serialize, x)
        # no arguments
        self.assertRaises(TypeError, serialize)
        # too many arguments
        self.assertRaises(TypeError, serialize, bitarray(), 1)

    # On Python 2, bytes(x) is the string representation of x,
    # so x can almost be of any type.  And the string representation
    # of these object will cause ValueErrors in bitarray(x).
    # Instead of adding special cases in deserialize() or here,
    # we decided to skip these tests for Python 2 altogether.
    @skipIf(sys.version_info[0] == 2)
    def test_deserialize_args(self):
        for x in 0, 1, False, True, None, u'', u'01', 0.0, [0, 0.6]:
            self.assertRaises(TypeError, deserialize, x)
        self.assertRaises(TypeError, deserialize, b'\x00', 1)
        self.assertRaises(ValueError, deserialize, [0, 256])

        b = b'\x03\x06'
        for s in b, bytearray(b), memoryview(b), iter(b):
            a = deserialize(s)
            self.assertEqual(a.endian(), 'little')
            self.assertEqual(a, bitarray('01100'))

    def test_invalid_bytes(self):
        self.assertRaises(ValueError, deserialize, b'')

        def check_msg(b):
            # Python 2: PyErr_Format() seems to handle "0x%02x"
            # incorrectly.  E.g. instead of "0x01", I get "0x1"
            if sys.version_info[0] == 3:
                msg = "invalid header byte: 0x%02x" % b[0]
                self.assertRaisesMessage(ValueError, msg, deserialize, b)

        for i in range(256):
            b = bytes(bytearray([i]))
            if i == 0 or i == 16:
                self.assertEqual(deserialize(b), bitarray())
            else:
                self.assertRaises(ValueError, deserialize, b)
                check_msg(b)

            b += b'\0'
            if i < 32 and i % 16 < 8:
                self.assertEqual(deserialize(b), zeros(8 - i % 8))
            else:
                self.assertRaises(ValueError, deserialize, b)
                check_msg(b)

    def test_bits_ignored(self):
        # the unused padding bits (with the last bytes) are ignored
        for b, a in [
                (b'\x07\x01', bitarray('1', 'little')),
                (b'\x07\x03', bitarray('1', 'little')),
                (b'\x07\xff', bitarray('1', 'little')),
                (b'\x17\x80', bitarray('1', 'big')),
                (b'\x17\xc0', bitarray('1', 'big')),
                (b'\x17\xff', bitarray('1', 'big')),
        ]:
            self.assertEQUAL(deserialize(b), a)

    def test_random(self):
        for a in self.randombitarrays():
            b = deserialize(serialize(a))
            self.assertEQUAL(a, b)
            self.check_obj(b)

tests.append(TestsSerialization)

# ---------------------------------------------------------------------------

class TestsHuffman(unittest.TestCase):

    def test_simple(self):
        freq = {0: 10, 'as': 2, None: 1.6}
        code = huffman_code(freq)
        self.assertEqual(len(code), 3)
        self.assertEqual(len(code[0]), 1)
        self.assertEqual(len(code['as']), 2)
        self.assertEqual(len(code[None]), 2)

    def test_endianness(self):
        freq = {'A': 10, 'B': 2, 'C': 5}
        for endian in 'big', 'little':
            code = huffman_code(freq, endian)
            self.assertEqual(len(code), 3)
            for v in code.values():
                self.assertEqual(v.endian(), endian)

    def test_wrong_arg(self):
        self.assertRaises(TypeError, huffman_code, [('a', 1)])
        self.assertRaises(TypeError, huffman_code, 123)
        self.assertRaises(TypeError, huffman_code, None)
        # cannot compare 'a' with 1
        self.assertRaises(TypeError, huffman_code, {'A': 'a', 'B': 1})
        # frequency map cannot be empty
        self.assertRaises(ValueError, huffman_code, {})

    def test_one_symbol(self):
        cnt = {'a': 1}
        code = huffman_code(cnt)
        self.assertEqual(code, {'a': bitarray('0')})
        for n in range(4):
            msg = n * ['a']
            a = bitarray()
            a.encode(code, msg)
            self.assertEqual(a.to01(), n * '0')
            self.assertEqual(a.decode(code), msg)
            a.append(1)
            self.assertRaises(ValueError, a.decode, code)
            self.assertRaises(ValueError, list, a.iterdecode(code))

    def check_tree(self, code):
        n = len(code)
        tree = decodetree(code)
        self.assertEqual(tree.todict(), code)
        # ensure tree has 2n-1 nodes (n symbol nodes and n-1 internal nodes)
        self.assertEqual(tree.nodes(), 2 * n - 1)
        # a proper Huffman tree is complete
        self.assertTrue(tree.complete())

    def test_balanced(self):
        n = 6
        freq = {}
        for i in range(2 ** n):
            freq[i] = 1
        code = huffman_code(freq)
        self.assertEqual(len(code), 2 ** n)
        self.assertTrue(all(len(v) == n for v in code.values()))
        self.check_tree(code)

    def test_unbalanced(self):
        N = 27
        freq = {}
        for i in range(N):
            freq[i] = 2 ** i
        code = huffman_code(freq)
        self.assertEqual(len(code), N)
        for i in range(N):
            self.assertEqual(len(code[i]), N - (1 if i <= 1 else i))
        self.check_tree(code)

    def test_counter(self):
        message = 'the quick brown fox jumps over the lazy dog.'
        code = huffman_code(Counter(message))
        a = bitarray()
        a.encode(code, message)
        self.assertEqual(''.join(a.decode(code)), message)
        self.check_tree(code)

    def test_random_list(self):
        plain = [randint(0, 100) for _ in range(500)]
        code = huffman_code(Counter(plain))
        a = bitarray()
        a.encode(code, plain)
        self.assertEqual(a.decode(code), plain)
        self.check_tree(code)

    def test_random_freq(self):
        for n in 2, 3, 5, randint(50, 200):
            # create Huffman code for n symbols
            code = huffman_code({i: random() for i in range(n)})
            self.check_tree(code)

tests.append(TestsHuffman)

# ---------------------------------------------------------------------------

class TestsCanonicalHuffman(unittest.TestCase, Util):

    def test_basic(self):
        plain = bytearray(b'the quick brown fox jumps over the lazy dog.')
        chc, count, symbol = canonical_huffman(Counter(plain))
        self.assertIsInstance(chc, dict)
        self.assertIsInstance(count, list)
        self.assertIsInstance(symbol, list)
        a = bitarray()
        a.encode(chc, plain)
        self.assertEqual(bytearray(a.iterdecode(chc)), plain)
        self.assertEqual(bytearray(canonical_decode(a, count, symbol)), plain)

    def test_canonical_huffman_errors(self):
        self.assertRaises(TypeError, canonical_huffman, [])
        # frequency map cannot be empty
        self.assertRaises(ValueError, canonical_huffman, {})
        self.assertRaises(TypeError, canonical_huffman)
        cnt = huffman_code(Counter('aabc'))
        self.assertRaises(TypeError, canonical_huffman, cnt, 'a')

    def test_one_symbol(self):
        cnt = {'a': 1}
        chc, count, symbol = canonical_huffman(cnt)
        self.assertEqual(chc, {'a': bitarray('0')})
        self.assertEqual(count, [0, 1])
        self.assertEqual(symbol, ['a'])
        for n in range(4):
            msg = n * ['a']
            a = bitarray()
            a.encode(chc, msg)
            self.assertEqual(a.to01(), n * '0')
            self.assertEqual(list(canonical_decode(a, count, symbol)), msg)
            a.append(1)
            self.assertRaises(ValueError, list,
                              canonical_decode(a, count, symbol))

    def test_canonical_decode_errors(self):
        a = bitarray('1101')
        s = ['a']
        # bitarray not of bitarray type
        self.assertRaises(TypeError, canonical_decode, '11', [0, 1], s)
        # count not sequence
        self.assertRaises(TypeError, canonical_decode, a, {0, 1}, s)
        # count element not an int
        self.assertRaises(TypeError, canonical_decode, a, [0, 1.0], s)
        # count element overflow
        self.assertRaises(OverflowError, canonical_decode, a, [0, 1 << 65], s)
        # negative count
        self.assertRaises(ValueError, canonical_decode, a, [0, -1], s)
        # count list too long
        self.assertRaises(ValueError, canonical_decode, a, 32 * [0], s)
        # symbol not sequence
        self.assertRaises(TypeError, canonical_decode, a, [0, 1], 43)

        symbol = ['a', 'b', 'c', 'd']
        # sum(count) != len(symbol)
        self.assertRaisesMessage(ValueError,
                                 "sum(count) = 3, but len(symbol) = 4",
                                 canonical_decode, a, [0, 1, 2], symbol)
        # count[i] > 1 << i
        self.assertRaisesMessage(ValueError,
                        "count[2] cannot be negative or larger than 4, got 5",
                        canonical_decode, a, [0, 2, 5], symbol)

    def test_canonical_decode_simple(self):
        # symbols can be anything, they do not even have to be hashable here
        cnt = [0, 0, 4]
        s = ['A', 42, [1.2-3.7j, 4j], {'B': 6}]
        a = bitarray('00 01 10 11')
        # count can be a list
        self.assertEqual(list(canonical_decode(a, cnt, s)), s)
        # count can also be a tuple (any sequence object in fact)
        self.assertEqual(list(canonical_decode(a, (0, 0, 4), s)), s)
        self.assertEqual(list(canonical_decode(7 * a, cnt, s)), 7 * s)
        # the count list may have extra 0's at the end (but not too many)
        count = [0, 0, 4, 0, 0, 0, 0, 0]
        self.assertEqual(list(canonical_decode(a, count, s)), s)
        # the element count[0] is unused
        self.assertEqual(list(canonical_decode(a, [-47, 0, 4], s)), s)
        # in fact it can be anything, as it is entirely ignored
        self.assertEqual(list(canonical_decode(a, [s, 0, 4], s)), s)

        # the symbol argument can be any sequence object
        s = [65, 66, 67, 98]
        self.assertEqual(list(canonical_decode(a, cnt, s)), s)
        self.assertEqual(list(canonical_decode(a, cnt, bytearray(s))), s)
        self.assertEqual(list(canonical_decode(a, cnt, tuple(s))), s)
        if sys.version_info[0] == 3:
            self.assertEqual(list(canonical_decode(a, cnt, bytes(s))), s)
        # Implementation Note:
        #   The symbol can even be an iterable.  This was done because we
        #   want to use PySequence_Fast in order to convert sequence
        #   objects (like bytes and bytearray) to a list.  This is faster
        #   as all objects are now elements in an array of pointers (as
        #   opposed to having the object's __getitem__ method called on
        #   every iteration).
        self.assertEqual(list(canonical_decode(a, cnt, iter(s))), s)

    def test_canonical_decode_empty(self):
        a = bitarray()
        # count and symbol are empty, ok because sum([]) == len([])
        self.assertEqual(list(canonical_decode(a, [], [])), [])
        a.append(0)
        self.assertRaisesMessage(ValueError, "reached end of bitarray",
                                 list, canonical_decode(a, [], []))
        a = bitarray(31 * '0')
        self.assertRaisesMessage(ValueError, "ran out of codes",
                                 list, canonical_decode(a, [], []))

    def test_canonical_decode_one_symbol(self):
        symbols = ['A']
        count = [0, 1]
        a = bitarray('000')
        self.assertEqual(list(canonical_decode(a, count, symbols)),
                         3 * symbols)
        a.append(1)
        a.extend(bitarray(10 * '0'))
        iterator = canonical_decode(a, count, symbols)
        self.assertRaisesMessage(ValueError, "reached end of bitarray",
                                 list, iterator)

        a.extend(bitarray(20 * '0'))
        iterator = canonical_decode(a, count, symbols)
        self.assertRaisesMessage(ValueError, "ran out of codes",
                                 list, iterator)

    def test_canonical_decode_large(self):
        with open(__file__, 'rb') as f:
            msg = bytearray(f.read())
        self.assertTrue(len(msg) > 50000)
        codedict, count, symbol = canonical_huffman(Counter(msg))
        a = bitarray()
        a.encode(codedict, msg)
        self.assertEqual(bytearray(canonical_decode(a, count, symbol)), msg)
        self.check_code(codedict, count, symbol)

    def test_canonical_decode_symbol_change(self):
        msg = bytearray(b"Hello World!")
        codedict, count, symbol = canonical_huffman(Counter(msg))
        self.check_code(codedict, count, symbol)
        a = bitarray()
        a.encode(codedict, 10 * msg)

        it = canonical_decode(a, count, symbol)
        def decode_one_msg():
            return bytearray(next(it) for _ in range(len(msg)))

        self.assertEqual(decode_one_msg(), msg)
        symbol[symbol.index(ord("l"))] = ord("k")
        self.assertEqual(decode_one_msg(), bytearray(b"Hekko Workd!"))
        del symbol[:]
        self.assertRaises(IndexError, decode_one_msg)

    def ensure_sorted(self, chc, symbol):
        # ensure codes are sorted
        for i in range(len(symbol) - 1):
            a = chc[symbol[i]]
            b = chc[symbol[i + 1]]
            self.assertTrue(ba2int(a) < ba2int(b))

    def ensure_consecutive(self, chc, count, symbol):
        first = 0
        for nbits, cnt in enumerate(count):
            for i in range(first, first + cnt - 1):
                # ensure two consecutive codes (with same bit length) have
                # consecutive integer values
                a = chc[symbol[i]]
                b = chc[symbol[i + 1]]
                self.assertTrue(len(a) == len(b) == nbits)
                self.assertEqual(ba2int(a) + 1, ba2int(b))
            first += cnt

    def ensure_count(self, chc, count):
        # ensure count list corresponds to length counts from codedict
        maxbits = max(len(a) for a in chc.values())
        my_count = (maxbits + 1) * [0]
        for a in chc.values():
            self.assertEqual(a.endian(), 'big')
            my_count[len(a)] += 1
        self.assertEqual(my_count, list(count))

    def ensure_complete(self, count):
        # ensure code is complete and not oversubscribed
        maxbits = len(count)
        x = sum(count[i] << (maxbits - i) for i in range(1, maxbits))
        self.assertEqual(x, 1 << maxbits)

    def ensure_complete_2(self, chc):
        # ensure code is complete
        dt = decodetree(chc)
        self.assertTrue(dt.complete())

    def ensure_round_trip(self, chc, count, symbol):
        # create a short test message, encode and decode
        msg = [choice(symbol) for _ in range(10)]
        a = bitarray()
        a.encode(chc, msg)
        it = canonical_decode(a, count, symbol)
        # the iterator holds a reference to the bitarray and symbol list
        del a, count, symbol
        self.assertEqual(type(it).__name__, 'canonical_decodeiter')
        self.assertEqual(list(it), msg)

    def check_code(self, chc, count, symbol):
        self.assertTrue(len(chc) == len(symbol) == sum(count))
        self.assertEqual(count[0], 0)  # no codes have length 0
        self.assertTrue(set(chc) == set(symbol))
        # the code of the last symbol has all 1 bits
        self.assertTrue(chc[symbol[-1]].all())
        # the code of the first symbol starts with bit 0
        self.assertFalse(chc[symbol[0]][0])

        self.ensure_sorted(chc, symbol)
        self.ensure_consecutive(chc, count, symbol)
        self.ensure_count(chc, count)
        self.ensure_complete(count)
        self.ensure_complete_2(chc)
        self.ensure_round_trip(chc, count, symbol)

    def test_simple_counter(self):
        plain = bytearray(b'the quick brown fox jumps over the lazy dog.')
        cnt = Counter(plain)
        code, count, symbol = canonical_huffman(cnt)
        self.check_code(code, count, symbol)
        self.check_code(code, tuple(count), tuple(symbol))
        self.check_code(code, bytearray(count), symbol)
        self.check_code(code, count, bytearray(symbol))

    def test_balanced(self):
        n = 7
        freq = {}
        for i in range(2 ** n):
            freq[i] = 1
        code, count, sym = canonical_huffman(freq)
        self.assertEqual(len(code), 2 ** n)
        self.assertTrue(all(len(v) == n for v in code.values()))
        self.check_code(code, count, sym)

    def test_unbalanced(self):
        n = 29
        freq = {}
        for i in range(n):
            freq[i] = 2 ** i
        code = canonical_huffman(freq)[0]
        self.assertEqual(len(code), n)
        for i in range(n):
            self.assertEqual(len(code[i]), n - (1 if i <= 1 else i))
        self.check_code(*canonical_huffman(freq))

    def test_random_freq(self):
        for n in 2, 3, 5, randint(50, 200):
            freq = {i: random() for i in range(n)}
            self.check_code(*canonical_huffman(freq))


tests.append(TestsCanonicalHuffman)

# ---------------------------------------------------------------------------

def run(verbosity=1):
    import bitarray

    print('bitarray.util is installed in: %s' % os.path.dirname(__file__))
    print('bitarray version: %s' % bitarray.__version__)
    print('Python version: %s' % sys.version)

    suite = unittest.TestSuite()
    for cls in tests:
        suite.addTest(unittest.makeSuite(cls))

    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


if __name__ == '__main__':
    run()
