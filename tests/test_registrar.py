from nose.tools import (
    eq_,
)
import json

from authentication_document import AuthenticationDocument
from opds import OPDSCatalog
from problem_details import *
from registrar import LibraryRegistrar
from testing import (
    DatabaseTest,
    DummyHTTPResponse,
)
from util.problem_detail import ProblemDetail


class TestRegistrar(DatabaseTest):

    # TODO: The core method, register(), is tested indirectly in
    # test_controller.py, because the LibraryRegistrar code was
    # originally part of LibraryRegistryController. This could be
    # refactored.

    def test_reregister(self):
        pass

    def test_opds_response_links(self):
        """Test the opds_response_links method.

        This method is used to find the link back from the OPDS document to
        the Authentication For OPDS document.

        It checks the Link header and the body of an OPDS 1 or OPDS 2
        document.

        This test also tests the related
        opds_response_links_to_auth_document, which checks whether a
        particular URL is found in the list of links.
        """
        auth_url = "http://circmanager.org/auth"
        rel = AuthenticationDocument.AUTHENTICATION_DOCUMENT_REL

        # An OPDS 1 feed that has a link.
        has_link_feed = '<feed><link rel="%s" href="%s"/></feed>' % (
            rel, auth_url
        )
        response = DummyHTTPResponse(
            200, {"Content-Type": OPDSCatalog.OPDS_1_TYPE}, has_link_feed
        )
        eq_([auth_url], LibraryRegistrar.opds_response_links(
            response, rel
        ))
        eq_(True,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )
        eq_(False,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, "Some other URL"
            )
        )

        # The same feed, but with an additional link in the
        # Link header. Both links are returned.
        response = DummyHTTPResponse(
            200, {"Content-Type": OPDSCatalog.OPDS_1_TYPE},
            has_link_feed, links={rel: {'url': "http://another-auth-document",
                                        'rel': rel}}
        )
        eq_(set([auth_url, "http://another-auth-document"]),
            set(LibraryRegistrar.opds_response_links(response, rel))
        )
        eq_(True,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )

        # A similar feed, but with a relative URL, which is made absolute
        # by opds_response_links.
        relative_url_feed = '<feed><link rel="%s" href="auth-document"/></feed>' % (
            rel
        )
        response = DummyHTTPResponse(
            200, {"Content-Type": OPDSCatalog.OPDS_1_TYPE}, relative_url_feed
        )
        response.url = "http://opds-server/catalog.opds"
        eq_(["http://opds-server/auth-document"],
            LibraryRegistrar.opds_response_links(response, rel)
        )
        eq_(True,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, "http://opds-server/auth-document"
            )
        )

        # An OPDS 1 feed that has no link.
        response = DummyHTTPResponse(
            200, {"Content-Type": OPDSCatalog.OPDS_1_TYPE}, "<feed></feed>"
        )
        eq_([], LibraryRegistrar.opds_response_links(
            response, rel
        ))
        eq_(False,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )

        # An OPDS 2 feed that has a link.
        catalog = json.dumps({"links": {rel: { "href": auth_url }}})
        response = DummyHTTPResponse(
            200, {"Content-Type": OPDSCatalog.OPDS_TYPE}, catalog
        )
        eq_([auth_url], LibraryRegistrar.opds_response_links(
            response, rel
        ))
        eq_(True,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )

        # An OPDS 2 feed that has no link.
        catalog = json.dumps({"links": {}})
        response = DummyHTTPResponse(
            200, {"Content-Type": OPDSCatalog.OPDS_TYPE}, catalog
        )
        eq_([], LibraryRegistrar.opds_response_links(
            response, rel
        ))
        eq_(False,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )

        # A malformed feed.
        response = DummyHTTPResponse(
            200, {"Content-Type": OPDSCatalog.OPDS_TYPE}, "Not a real feed"
        )
        eq_(False,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )

        # An Authentication For OPDS document.
        response = DummyHTTPResponse(
            200, {"Content-Type": AuthenticationDocument.MEDIA_TYPE},
            json.dumps({ "id": auth_url })
        )
        eq_([auth_url], LibraryRegistrar.opds_response_links(
            response, rel
        ))
        eq_(True,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )

        # A malformed Authentication For OPDS document.
        response = DummyHTTPResponse(
            200, {"Content-Type": AuthenticationDocument.MEDIA_TYPE},
            json.dumps("Not a document.")
        )
        eq_([], LibraryRegistrar.opds_response_links(
            response, rel
        ))
        eq_(False,
            LibraryRegistrar.opds_response_links_to_auth_document(
                response, auth_url
            )
        )

    def test__required_email_address(self):
        """Validate the code that makes sure an input is a mailto: URI."""
        uri = INVALID_CONTACT_URI.uri
        m = LibraryRegistrar._required_email_address

        problem = m(None, 'a title')
        eq_(uri, problem.uri)
        # The custom title is used.
        eq_("a title", problem.title)
        eq_("No email address was provided", problem.detail)

        # Changing the title doesn't affect the original ProblemDetail
        # document.
        assert "a title" != INVALID_CONTACT_URI.title

        problem = m("http://not-an-email/", "a title")
        eq_(uri, problem.uri)
        eq_("URI must start with 'mailto:' (got: http://not-an-email/)",
            problem.detail)

        mailto = "mailto:me@library.org"
        success = m(mailto, "a title")
        eq_(mailto, success)

    def test__locate_email_addresses(self):
        """Test the code that finds an email address in a list of links."""
        uri = INVALID_CONTACT_URI.uri
        m = LibraryRegistrar._locate_email_addresses

        # No links at all.
        result = m("rel0", [], "a title")
        assert isinstance(result, ProblemDetail)
        eq_(uri, result.uri)
        eq_("a title", result.title)
        eq_("No valid mailto: links found with rel=rel0", result.detail)

        # Links exist but none are valid and relevant.
        links = [dict(rel="rel1", href="http://foo/"),
                 dict(rel="rel1", href="http://bar/"),
                 dict(rel="rel2", href="mailto:me@library.org"),
                 dict(rel="rel2", href="mailto:me2@library.org"),
        ]
        result = m("rel1", links, "a title")
        assert isinstance(result, ProblemDetail)
        eq_(uri, result.uri)
        eq_("a title", result.title)
        eq_("No valid mailto: links found with rel=rel1", result.detail)

        # Multiple links that work.
        result = m("rel2", links, "a title")
        eq_(["mailto:me@library.org", "mailto:me2@library.org"], result)

    def test__update_library_authentication_url(self):
        """Test the code that modifies Library.authentication_url
        and Library.opds_url if the right shared secret was provided.
        """
        library = self._library()
        secret = "it's a secret"
        library.shared_secret = secret
        library.authentication_url = "old auth"
        library.opds_url = "old opds"

        m = LibraryRegistrar._update_library_authentication_url
        problem = m(library, "new auth", "new opds", "wrong secret")
        eq_(AUTHENTICATION_FAILURE.uri, problem.uri)
        eq_("Provided shared secret is invalid", problem.detail)
        eq_("old auth", library.authentication_url)

        result = m(library, "new auth", "new opds", secret)
        eq_(result, None)
        eq_("new auth", library.authentication_url)
        eq_("new opds", library.opds_url)

        # If a value is missing, the field isn't changed.
        result = m(library, None, None, secret)
        eq_(result, None)
        eq_("new auth", library.authentication_url)
        eq_("new opds", library.opds_url)
