import unittest
from capybara.test.test_worker import TestWorker


class CountSolutionsTestCase(unittest.TestCase):
    def test_SFC_m111(self):
        worker = TestWorker('SFC.nex', -1, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 40)

    def test_SFC_0111(self):
        worker = TestWorker('SFC.nex', 0, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 184)

    def test_SFC_0121(self):
        worker = TestWorker('SFC.nex', 0, 1, 2, 1, task=0)
        self.assertEqual(worker.get_answer(), 40)

    def test_SFC_0110(self):
        worker = TestWorker('SFC.nex', 0, 1, 1, 0, task=0)
        self.assertEqual(worker.get_answer(), 6332)

    def test_RH_m111(self):
        worker = TestWorker('RH.nex', -1, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 1056)

    def test_RH_0111(self):
        worker = TestWorker('RH.nex', 0, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 42)

    def test_RH_0121(self):
        worker = TestWorker('RH.nex', 0, 1, 2, 1, task=0)
        self.assertEqual(worker.get_answer(), 2208)

    def test_RH_0110(self):
        worker = TestWorker('RH.nex', 0, 1, 1, 0, task=0)
        self.assertEqual(worker.get_answer(), 4080384)

    def test_COG3715_m111(self):
        worker = TestWorker('COG3715.nex', -1, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 63360)

    def test_COG3715_0111(self):
        worker = TestWorker('COG3715.nex', 0, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 1172598)

    def test_COG4965_m111(self):
        worker = TestWorker('COG4965.nex', -1, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 44800)

    def test_COG4965_0111(self):
        worker = TestWorker('COG4965.nex', 0, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 17408)

    def test_COG4965_0121(self):
        worker = TestWorker('COG4965.nex', 0, 1, 2, 1, task=0)
        self.assertEqual(worker.get_answer(), 640)

    def test_COG4965_0231(self):
        worker = TestWorker('COG4965.nex', 0, 2, 3, 1, task=0)
        self.assertEqual(worker.get_answer(), 6528)

    def test_COG4965_0110(self):
        worker = TestWorker('COG4965.nex', 0, 1, 1, 0, task=0)
        self.assertEqual(worker.get_answer(), 907176)

    def test_COG2085_m111(self):
        worker = TestWorker('COG2085.nex', -1, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 109056)

    def test_COG2085_0111(self):
        worker = TestWorker('COG2085.nex', 0, 1, 1, 1, task=0)
        self.assertEqual(worker.get_answer(), 44544)

    def test_COG2085_0121(self):
        worker = TestWorker('COG2085.nex', 0, 1, 2, 1, task=0)
        self.assertEqual(worker.get_answer(), 37568)

    def test_COG2085_0231(self):
        worker = TestWorker('COG2085.nex', 0, 2, 3, 1, task=0)
        self.assertEqual(worker.get_answer(), 46656)

