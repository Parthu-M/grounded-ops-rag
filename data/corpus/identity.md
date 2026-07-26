# Nimbus Identity and Access.

Nimbus access tokens expire after 15 minutes. Refresh tokens remain valid for 30 days unless they are revoked. Administrators can require multi-factor authentication for every member of an organization. Nimbus supports authenticator applications and WebAuthn security keys as second factors.

Single sign-on is available on the Enterprise plan through SAML 2.0. Just-in-time provisioning can create a member after a successful SAML login. SCIM provisioning synchronizes users and groups from the identity provider every 40 minutes. A suspended user loses access immediately, while their owned projects remain in the organization.

API keys belong to service accounts rather than individual employees. Each service account can hold at most five active API keys. Secret values are shown only once when a key is created. Rotation is performed by creating a replacement key, deploying it, and then revoking the old key.

