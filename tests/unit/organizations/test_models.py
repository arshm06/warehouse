# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from pyramid.authorization import Allow
from pyramid.location import lineage

from warehouse.organizations.models import OrganizationFactory, OrganizationRoleType

from ...common.db.organizations import (
    OrganizationFactory as DBOrganizationFactory,
    OrganizationRoleFactory as DBOrganizationRoleFactory,
)


class TestOrganizationFactory:
    @pytest.mark.parametrize(("name", "normalized"), [("foo", "foo"), ("Bar", "bar")])
    def test_traversal_finds(self, db_request, name, normalized):
        organization = DBOrganizationFactory.create(name=name)
        root = OrganizationFactory(db_request)

        assert root[normalized] == organization

    def test_traversal_cant_find(self, db_request):
        organization = DBOrganizationFactory.create()
        root = OrganizationFactory(db_request)

        with pytest.raises(KeyError):
            root[organization.name + "invalid"]


class TestOrganization:
    def test_acl(self, db_session):
        organization = DBOrganizationFactory.create()
        owner1 = DBOrganizationRoleFactory.create(organization=organization)
        owner2 = DBOrganizationRoleFactory.create(organization=organization)
        billing_mgr1 = DBOrganizationRoleFactory.create(
            organization=organization, role_name=OrganizationRoleType.BillingManager
        )
        billing_mgr2 = DBOrganizationRoleFactory.create(
            organization=organization, role_name=OrganizationRoleType.BillingManager
        )
        account_mgr1 = DBOrganizationRoleFactory.create(
            organization=organization, role_name=OrganizationRoleType.Manager
        )
        account_mgr2 = DBOrganizationRoleFactory.create(
            organization=organization, role_name=OrganizationRoleType.Manager
        )
        member1 = DBOrganizationRoleFactory.create(
            organization=organization, role_name=OrganizationRoleType.Member
        )
        member2 = DBOrganizationRoleFactory.create(
            organization=organization, role_name=OrganizationRoleType.Member
        )

        acls = []
        for location in lineage(organization):
            try:
                acl = location.__acl__
            except AttributeError:
                continue

            if acl and callable(acl):
                acl = acl()

            acls.extend(acl)

        assert acls == [
            (Allow, "group:admins", "admin"),
            (Allow, "group:moderators", "moderator"),
        ] + sorted(
            [
                (
                    Allow,
                    f"user:{owner1.user.id}",
                    ["view:organization", "manage:organization"],
                ),
                (
                    Allow,
                    f"user:{owner2.user.id}",
                    ["view:organization", "manage:organization"],
                ),
            ],
            key=lambda x: x[1],
        ) + sorted(
            [
                (
                    Allow,
                    f"user:{billing_mgr1.user.id}",
                    ["view:organization", "manage:billing"],
                ),
                (
                    Allow,
                    f"user:{billing_mgr2.user.id}",
                    ["view:organization", "manage:billing"],
                ),
            ],
            key=lambda x: x[1],
        ) + sorted(
            [
                (
                    Allow,
                    f"user:{account_mgr1.user.id}",
                    ["view:organization", "manage:team"],
                ),
                (
                    Allow,
                    f"user:{account_mgr2.user.id}",
                    ["view:organization", "manage:team"],
                ),
            ],
            key=lambda x: x[1],
        ) + sorted(
            [
                (Allow, f"user:{member1.user.id}", ["view:organization"]),
                (Allow, f"user:{member2.user.id}", ["view:organization"]),
            ],
            key=lambda x: x[1],
        )