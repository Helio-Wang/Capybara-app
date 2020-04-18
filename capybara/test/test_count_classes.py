import unittest
from capybara.test.test_worker import TestWorker


class CountClassesTestCase(unittest.TestCase):
    def test_SFC_m111(self):
        worker = TestWorker('SFC.nex', -1, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 3)

    def test_SFC_0111(self):
        worker = TestWorker('SFC.nex', 0, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 6)

    def test_SFC_0121(self):
        worker = TestWorker('SFC.nex', 0, 1, 2, 1, task=3)
        self.assertEqual(worker.get_answer(), 3)

    def test_SFC_0110(self):
        worker = TestWorker('SFC.nex', 0, 1, 1, 0, task=3)
        self.assertEqual(worker.get_answer(), 888)

    def test_RH_m111(self):
        worker = TestWorker('RH.nex', -1, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 64)

    def test_RH_0111(self):
        worker = TestWorker('RH.nex', 0, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 8)

    def test_RH_0121(self):
        worker = TestWorker('RH.nex', 0, 1, 2, 1, task=3)
        self.assertEqual(worker.get_answer(), 196)

    def test_COG3715_m111(self):
        worker = TestWorker('COG3715.nex', -1, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 32)

    def test_COG3715_0111(self):
        worker = TestWorker('COG3715.nex', 0, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 872)

    def test_COG4965_m111(self):
        worker = TestWorker('COG4965.nex', -1, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 13)

    def test_COG4965_0111(self):
        worker = TestWorker('COG4965.nex', 0, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 4)

    def test_COG4965_0121(self):
        worker = TestWorker('COG4965.nex', 0, 1, 2, 1, task=3)
        self.assertEqual(worker.get_answer(), 3)

    def test_COG4965_0231(self):
        worker = TestWorker('COG4965.nex', 0, 2, 3, 1, task=3)
        self.assertEqual(worker.get_answer(), 5)

    def test_COG4965_0110(self):
        worker = TestWorker('COG4965.nex', 0, 1, 1, 0, task=3)
        self.assertEqual(worker.get_answer(), 11958)

    def test_COG2085_m111(self):
        worker = TestWorker('COG2085.nex', -1, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 6)

    def test_COG2085_0111(self):
        worker = TestWorker('COG2085.nex', 0, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 4)

    def test_COG2085_0121(self):
        worker = TestWorker('COG2085.nex', 0, 1, 2, 1, task=3)
        self.assertEqual(worker.get_answer(), 14)

    def test_COG2085_0231(self):
        worker = TestWorker('COG2085.nex', 0, 2, 3, 1, task=3)
        self.assertEqual(worker.get_answer(), 10)

    def test_wolb_m111(self):
        worker = TestWorker('Wolbachia.nex', -1, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 24192)

    def test_wolb_0111(self):
        worker = TestWorker('Wolbachia.nex', 0, 1, 1, 1, task=3)
        self.assertEqual(worker.get_answer(), 76800)

