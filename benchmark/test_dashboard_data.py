import unittest
from dashboard_data import comparison_rows


def job(model,chat,status,task='KMMLU',metrics=None,**extra):
    return dict(model=model,chat=chat,status=status,task=task,metrics=metrics or [],category='Korean knowledge',warnings=[],**extra)


class PairedResultsTests(unittest.TestCase):
    def test_pending_domain_results_pair_with_completed_domains(self):
        data={'jobs':[job('mkd-hossain/Keural-Cortex-8B-v1.0',False,'completed',metrics=[{'task':'kmmlu_economics','metric':'acc,none','value':.6,'n':10}]),
                      job('Qwen/Qwen3-8B-Base',False,'pending')]}
        rows=comparison_rows(data,'completion')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['qwen']['status'],'pending')
        self.assertEqual(rows[0]['cortex']['value'],.6)

    def test_assistant_does_not_reuse_raw_completion_status(self):
        data={'jobs':[job('mkd-hossain/Keural-Cortex-8B-v1.0',False,'completed'),
                      job('mkd-hossain/Keural-Cortex-8B-v1.0',True,'pending'),
                      job('Qwen/Qwen3-8B',True,'completed',metrics=[{'task':'kmmlu_economics','metric':'acc,none','value':.7,'n':10}])]}
        rows=comparison_rows(data,'assistant')
        self.assertEqual(rows[0]['cortex']['status'],'pending')

    def test_64k_has_no_fabricated_comparator(self):
        data={'jobs':[job('mkd-hossain/Keural-Cortex-8B-v1.0',None,'completed',task='Long context 64K',runner='diagnostics',suite='long-context',context=65536,
                           metrics=[{'task':'Long context','metric':'pass_rate','value':1.,'n':2}])]}
        row=comparison_rows(data,'context')[0]
        self.assertTrue(row['extension'])
        self.assertEqual(row['qwen']['status'],'not-applicable')


if __name__=='__main__':
    unittest.main()
