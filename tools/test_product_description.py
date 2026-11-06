import unittest
import build_pages as bp

class ProductDescriptionTests(unittest.TestCase):
    def test_icloud_account_is_a_feature_not_billing_terms(self):
        for lang in ['de','ja','th']:
            app=next(a for a in bp.APPS if a['key']=='countdown-'+lang)
            description=bp.store_of(app)['description']
            for old,new in app['descriptionReplacements'].items(): description=description.replace(old,new)
            _,sections,fine=bp.parse_desc(description)
            recovery=next(s for s in sections if any('30' in p and 'iCloud' in p for p in s['paras']))
            self.assertTrue(recovery['paras'])
            self.assertFalse(any('30' in line and 'iCloud' in line for b in fine for line in b))
            self.assertTrue(fine, 'Real subscription terms remain in fine print')
    def test_billing_after_separator_stays_in_fine_print(self):
        _,_,fine=bp.parse_desc('Features\nUse your Apple Account for iCloud sync.\n\n———\nPayment is charged to your Apple Account.')
        self.assertEqual(fine,[['Payment is charged to your Apple Account.']])

if __name__=='__main__': unittest.main()
