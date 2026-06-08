from tests.test_base import BaseTestCase
from models import User, Module, UserPermission
from index import db
from core.permissions import (
    get_perm, get_sub_perm, can_view_material_type, 
    require_perm, require_sub_perm
)
from flask_login import login_user

class TestPermissions(BaseTestCase):
    def test_admin_has_full_permissions(self):
        # Test inside request context
        with self.app.test_request_context():
            login_user(self.admin_user)
            
            # Admin should get FullPerm on any module, even non-existent ones
            perm = get_perm('dashboard')
            self.assertTrue(perm.can_view)
            self.assertTrue(perm.can_add)
            self.assertTrue(perm.can_edit)
            self.assertTrue(perm.can_delete)

            perm_fake = get_perm('nonexistent_module')
            self.assertTrue(perm_fake.can_view)
        
    def test_admin_sub_permissions_always_allowed(self):
        with self.app.test_request_context():
            login_user(self.admin_user)
            # Admin should always have sub permissions
            self.assertTrue(get_sub_perm('crm_leads', 'any_sub_perm'))

    def test_regular_user_no_permissions_by_default(self):
        with self.app.test_request_context():
            login_user(self.regular_user)
            
            # Without UserPermission row, should get NoPerm
            perm = get_perm('crm_leads')
            self.assertFalse(perm.can_view)
            self.assertFalse(perm.can_add)
            
            # Sub perms should return False
            self.assertFalse(get_sub_perm('crm_leads', 'filter'))

    def test_regular_user_with_explicit_permissions(self):
        # Get module id
        mod = Module.query.filter_by(name='crm_leads').first()
        self.assertIsNotNone(mod)

        # Create user permission record
        user_perm = UserPermission(
            user_id=self.regular_user.id,
            module_id=mod.id,
            can_view=True,
            can_add=True,
            can_edit=False,
            can_delete=False
        )
        user_perm.set_sub_permissions({'filter': True, 'sort': False})
        db.session.add(user_perm)
        db.session.commit()

        # Run checks inside request context
        with self.app.test_request_context():
            login_user(self.regular_user)

            # Check permission check methods
            perm = get_perm('crm_leads')
            self.assertTrue(perm.can_view)
            self.assertTrue(perm.can_add)
            self.assertFalse(perm.can_edit)

            # Check sub permissions
            self.assertTrue(get_sub_perm('crm_leads', 'filter'))
            self.assertFalse(get_sub_perm('crm_leads', 'sort'))
            self.assertFalse(get_sub_perm('crm_leads', 'whatsapp')) # missing in dict

    def test_can_view_material_type_rules(self):
        # Admin and Manager can view all
        with self.app.test_request_context():
            login_user(self.admin_user)
            self.assertTrue(can_view_material_type('RM'))
            self.assertTrue(can_view_material_type('PM'))
            self.assertTrue(can_view_material_type('FG'))

        # Regular user without permissions
        with self.app.test_request_context():
            login_user(self.regular_user)
            self.assertFalse(can_view_material_type('RM'))
        
        # Grant view permission on purchase_rm
        mod_rm = Module.query.filter_by(name='purchase_rm').first()
        user_perm = UserPermission(
            user_id=self.regular_user.id,
            module_id=mod_rm.id,
            can_view=True
        )
        db.session.add(user_perm)
        db.session.commit()
        
        with self.app.test_request_context():
            login_user(self.regular_user)
            self.assertTrue(can_view_material_type('RM'))
            self.assertFalse(can_view_material_type('PM')) # still false

    def test_permission_decorators_restrict_access(self):
        with self.app.test_request_context():
            login_user(self.regular_user)

            # Define dummy function wrapped in decorators
            @require_perm('crm_leads', 'view')
            def mock_view_func():
                return "view_success"

            @require_perm('crm_leads', 'add')
            def mock_add_func():
                return "add_success"

            @require_sub_perm('crm_leads', 'filter')
            def mock_sub_func():
                return "sub_success"

            # 1. Accessing view should return 403 rendering error page
            res = mock_view_func()
            self.assertIsInstance(res, tuple)
            self.assertEqual(res[1], 403)
            self.assertIn('permission to access this page', res[0])

            # 2. Accessing add should redirect to dashboard with flash error
            res_add = mock_add_func()
            self.assertEqual(res_add.status_code, 302)
            self.assertTrue(res_add.location.endswith('/'))

            # 3. Accessing sub_perm should return 403
            res_sub = mock_sub_func()
            self.assertEqual(res_sub[1], 403)
