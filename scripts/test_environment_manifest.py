"""Pure offline checks for manifest completeness and publication safeguards."""
import copy,unittest
from environment_manifest import SERVICES,validate_manifest

def example():
    return {'run_id':'run-example','phase':'before','host':{'hardware':{'physical_memory_bytes':1024,'cpu_model':'test'}},
        'engine':{'Version':'test'},'python':{'version':'test'},'dependencies':{'test':'1'},
        'source_sha256':{'app/main.py':'a'*64},'dataset':{'status':'observed','transaction_read_only':True},
        'test_conditions':{'source':'test'},'containers':{'services':{name:{'state':'running','image_id':'sha256:'+'a'*64} for name in SERVICES},
            'versions':{name:{'status':'observed','value':'test'} for name in ['postgres','keycloak','opa','openbao','gateway','restic']}},
        'run':{'status':'pending','run_id':'run-example'}}

class ManifestChecks(unittest.TestCase):
    def test_complete_before_manifest(self):
        self.assertEqual(validate_manifest(example()),{'complete':True,'errors':[],'warnings':[]})
    def test_missing_service_rejected(self):
        value=example();del value['containers']['services']['api']
        self.assertFalse(validate_manifest(value)['complete'])
    def test_stopped_service_rejected(self):
        value=example();value['containers']['services']['opa']['state']='exited'
        self.assertFalse(validate_manifest(value)['complete'])
    def test_unobserved_dataset_rejected(self):
        value=example();value['dataset']['transaction_read_only']=False
        self.assertFalse(validate_manifest(value)['complete'])
    def test_after_requires_matching_results(self):
        value=example();value['phase']='after'
        self.assertFalse(validate_manifest(value)['complete'])
        value['run']={'status':'observed','run_id':'different'}
        self.assertFalse(validate_manifest(value)['complete'])
    def test_changed_source_or_image_rejected(self):
        for key in ['source_unchanged','service_images_unchanged']:
            value=example();value['comparison']={key:False}
            self.assertFalse(validate_manifest(value)['complete'])
    def test_expected_dataset_changes_do_not_fail(self):
        value=example();value['comparison']={'source_unchanged':True,'service_images_unchanged':True,
                                            'dataset_content_unchanged':False,'logical_state_unchanged':False}
        self.assertTrue(validate_manifest(value)['complete'])
    def test_unknown_ram_is_explicit_warning(self):
        value=example();value['host']['hardware']['physical_memory_bytes']=None
        result=validate_manifest(value)
        self.assertTrue(result['complete']);self.assertIn('Unknown host physical_memory_bytes',result['warnings'])
    def test_catalog_mismatch_gates_baseline_only(self):
        value=example();value['test_conditions']['dataset_catalog']={'dataset_version':'business-v1','document_id_content_sha256':'a'}
        value['dataset'].update(dataset_version='older',document_id_content_sha256='b')
        self.assertFalse(validate_manifest(value)['complete'])
        value['phase']='after';value['run']={'status':'observed','run_id':'run-example'}
        result=validate_manifest(value)
        self.assertTrue(result['complete']);self.assertIn('Live dataset differs from the static baseline catalog',result['warnings'])
    def test_credentials_and_keys_rejected(self):
        for secret in ['postgresql://user:password@database/test','Bearer sample.token.value','-----BEGIN PRIVATE KEY-----']:
            value=example();value['unsafe']=secret
            self.assertFalse(validate_manifest(value)['complete'])

if __name__=='__main__':unittest.main()
