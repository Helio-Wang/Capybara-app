import unittest
from .test_worker import TestWorker


class CountEventPartitionsTestCase(unittest.TestCase):
    def test_SFC_m111(self):
        worker = TestWorker('tests/datasets/SFC.nex', -1, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 3)

    def test_SFC_0111(self):
        worker = TestWorker('tests/datasets/SFC.nex', 0, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 6)

    def test_SFC_0121(self):
        worker = TestWorker('tests/datasets/SFC.nex', 0, 1, 2, 1, task=2)
        self.assertEqual(worker.get_answer(), 3)

    def test_SFC_0110(self):
        worker = TestWorker('tests/datasets/SFC.nex', 0, 1, 1, 0, task=2)
        self.assertEqual(worker.get_answer(), 70)

    def test_SFC_0000(self):
        worker = TestWorker('tests/datasets/SFC.nex', 0, 0, 0, 0, task=2)
        self.assertEqual(worker.get_answer(), 34011)

    def test_RH_m111(self):
        worker = TestWorker('tests/datasets/RH.nex', -1, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 12)

    def test_RH_0111(self):
        worker = TestWorker('tests/datasets/RH.nex', 0, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 4)

    def test_RH_0121(self):
        worker = TestWorker('tests/datasets/RH.nex', 0, 1, 2, 1, task=2)
        self.assertEqual(worker.get_answer(), 38)

    def test_RH_0110(self):
        worker = TestWorker('tests/datasets/RH.nex', 0, 1, 1, 0, task=2)
        self.assertEqual(worker.get_answer(), 1152)

    def test_COG3715_m111(self):
        worker = TestWorker('tests/datasets/COG3715.nex', -1, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 16)

    def test_COG3715_0111(self):
        worker = TestWorker('tests/datasets/COG3715.nex', 0, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 792)

    def test_COG3715_0110(self):
        worker = TestWorker('tests/datasets/COG3715.nex', 0, 1, 1, 0, task=2)
        self.assertEqual(worker.get_answer(), 2496)

    def test_COG4965_m111(self):
        worker = TestWorker('tests/datasets/COG4965.nex', -1, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 13)

    def test_COG4965_0111(self):
        worker = TestWorker('tests/datasets/COG4965.nex', 0, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 4)

    def test_COG4965_0121(self):
        worker = TestWorker('tests/datasets/COG4965.nex', 0, 1, 2, 1, task=2)
        self.assertEqual(worker.get_answer(), 3)

    def test_COG4965_0231(self):
        worker = TestWorker('tests/datasets/COG4965.nex', 0, 2, 3, 1, task=2)
        self.assertEqual(worker.get_answer(), 5)

    def test_COG4965_0110(self):
        worker = TestWorker('tests/datasets/COG4965.nex', 0, 1, 1, 0, task=2)
        self.assertEqual(worker.get_answer(), 12)

    def test_COG2085_m111(self):
        worker = TestWorker('tests/datasets/COG2085.nex', -1, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 6)

    def test_COG2085_0111(self):
        worker = TestWorker('tests/datasets/COG2085.nex', 0, 1, 1, 1, task=2)
        self.assertEqual(worker.get_answer(), 4)

    def test_COG2085_0121(self):
        worker = TestWorker('tests/datasets/COG2085.nex', 0, 1, 2, 1, task=2)
        self.assertEqual(worker.get_answer(), 14)

    def test_COG2085_0231(self):
        worker = TestWorker('tests/datasets/COG2085.nex', 0, 2, 3, 1, task=2)
        self.assertEqual(worker.get_answer(), 4)

    def test_COG2085_0110(self):
        worker = TestWorker('tests/datasets/COG2085.nex', 0, 1, 1, 0, task=2)
        self.assertEqual(worker.get_answer(), 1152)

    # def test_wolb_m111(self):
    #     worker = TestWorker('tests/datasets/Wolbachia.nex', -1, 1, 1, 1, task=2)
    #     self.assertEqual(worker.get_answer(), 4080)
    #
    # def test_wolb_0111(self):
    #     worker = TestWorker('tests/datasets/Wolbachia.nex', 0, 1, 1, 1, task=2)
    #     self.assertEqual(worker.get_answer(), 40960)

