//
// SerializationHelpers.cpp
//
// Packages a username + password into a KERB_INTERACTIVE_UNLOCK_LOGON blob
// that Windows LSA can verify directly, replacing the unreliable
// CredPackAuthenticationBufferW approach.
//

#include "SerializationHelpers.h"

// SECURITY_WIN32 is already defined in Common.h (which is pulled in via
// SerializationHelpers.h), so we can safely include the security headers.
#include <ntsecapi.h>

// ── helpers ──────────────────────────────────────────────────────────────────

//
// Open a connection to LSA and look up the Negotiate authentication package id.
//
static HRESULT GetNegotiateAuthPackageId(ULONG* pAuthPackage)
{
    if (!pAuthPackage)
        return E_POINTER;

    *pAuthPackage = 0;

    HANDLE lsa = nullptr;
    NTSTATUS st = LsaConnectUntrusted(&lsa);
    if (st != 0)
        return HRESULT_FROM_WIN32(LsaNtStatusToWinError(st));

    LSA_STRING name{};
    name.Buffer        = const_cast<PCHAR>("Negotiate");
    name.Length        = static_cast<USHORT>(strlen(name.Buffer));
    name.MaximumLength = name.Length + 1;

    st = LsaLookupAuthenticationPackage(lsa, &name, pAuthPackage);
    LsaDeregisterLogonProcess(lsa);

    if (st != 0)
        return HRESULT_FROM_WIN32(LsaNtStatusToWinError(st));

    return S_OK;
}

//
// Given what the user typed, produce domain + username suitable for LSA.
//
// Rules:
//   "rihem"          -> domain = COMPUTERNAME,  user = "rihem"
//   ".\rihem"        -> domain = COMPUTERNAME,  user = "rihem"
//   "DOMAIN\user"    -> domain = "DOMAIN",       user = "user"
//
static void SplitOrDefaultDomain(
    const std::wstring& input,
    std::wstring&       outDomain,
    std::wstring&       outUser)
{
    const auto pos = input.find(L'\\');
    if (pos != std::wstring::npos)
    {
        std::wstring domainPart = input.substr(0, pos);
        outUser = input.substr(pos + 1);

        if (domainPart == L".")
        {
            // ".\user" -> local machine
            wchar_t buf[MAX_COMPUTERNAME_LENGTH + 1] = {};
            DWORD   sz = MAX_COMPUTERNAME_LENGTH + 1;
            GetComputerNameW(buf, &sz);
            outDomain = buf;
        }
        else
        {
            outDomain = domainPart;
        }
    }
    else
    {
        // No backslash -> local account
        wchar_t buf[MAX_COMPUTERNAME_LENGTH + 1] = {};
        DWORD   sz = MAX_COMPUTERNAME_LENGTH + 1;
        GetComputerNameW(buf, &sz);
        outDomain = buf;
        outUser   = input;
    }
}

//
// Initialise a UNICODE_STRING from a std::wstring without allocating.
// The UNICODE_STRING points directly into the wstring's buffer.
//
static void UnicodeStringInitWithString(
    const std::wstring& src,
    UNICODE_STRING&     dst)
{
    dst.Length        = static_cast<USHORT>(src.size() * sizeof(wchar_t));
    dst.MaximumLength = dst.Length + sizeof(wchar_t);
    dst.Buffer        = const_cast<PWSTR>(src.c_str());
}

// CredProtectW is not used: KERB_INTERACTIVE_UNLOCK_LOGON is submitted
// directly to LSA, which accepts the plaintext password and handles
// hashing/encryption internally.  CredProtectW is only relevant when
// persisting credentials to the Credential Manager vault.

// ── KERB_INTERACTIVE_UNLOCK_LOGON packing ────────────────────────────────────

//
// Fill a KERB_INTERACTIVE_UNLOCK_LOGON with the three UNICODE_STRINGs
// pointing into the caller-owned std::wstrings.  MessageType is set
// according to usageScenario.
//
static void KerbInteractiveUnlockLogonInit(
    const std::wstring&             domain,
    const std::wstring&             user,
    const std::wstring&             password,
    CREDENTIAL_PROVIDER_USAGE_SCENARIO usageScenario,
    KERB_INTERACTIVE_UNLOCK_LOGON&  kiul)
{
    ZeroMemory(&kiul, sizeof(kiul));

    KERB_INTERACTIVE_LOGON& kil = kiul.Logon;

    kil.MessageType =
        (usageScenario == CPUS_UNLOCK_WORKSTATION)
            ? KerbWorkstationUnlockLogon
            : KerbInteractiveLogon;

    UnicodeStringInitWithString(domain,   kil.LogonDomainName);
    UnicodeStringInitWithString(user,     kil.UserName);
    UnicodeStringInitWithString(password, kil.Password);
}

//
// Serialise the KERB_INTERACTIVE_UNLOCK_LOGON into a flat CoTaskMemAlloc blob.
//
// The UNICODE_STRING.Buffer fields in the serialised blob must be byte offsets
// from the start of the structure (not absolute pointers), because LSA will
// re-base them after copying.
//
static HRESULT KerbInteractiveUnlockLogonPack(
    const KERB_INTERACTIVE_UNLOCK_LOGON& kiul,
    BYTE**                               ppPackedBlob,
    DWORD*                               pcbPackedBlob)
{
    if (!ppPackedBlob || !pcbPackedBlob)
        return E_POINTER;

    *ppPackedBlob   = nullptr;
    *pcbPackedBlob  = 0;

    const KERB_INTERACTIVE_LOGON& kil = kiul.Logon;

    // Total size = struct + the three string payloads (each already has a
    // MaximumLength that includes a NUL terminator).
    const DWORD cbStruct  = sizeof(KERB_INTERACTIVE_UNLOCK_LOGON);
    const DWORD cbDomain  = kil.LogonDomainName.MaximumLength;
    const DWORD cbUser    = kil.UserName.MaximumLength;
    const DWORD cbPass    = kil.Password.MaximumLength;
    const DWORD cbTotal   = cbStruct + cbDomain + cbUser + cbPass;

    BYTE* blob = static_cast<BYTE*>(CoTaskMemAlloc(cbTotal));
    if (!blob)
        return E_OUTOFMEMORY;

    ZeroMemory(blob, cbTotal);

    // Copy the struct header.
    CopyMemory(blob, &kiul, cbStruct);

    // Re-interpret the header in the blob so we can patch the Buffer offsets.
    auto* pKiul = reinterpret_cast<KERB_INTERACTIVE_UNLOCK_LOGON*>(blob);
    KERB_INTERACTIVE_LOGON& pKil = pKiul->Logon;

    DWORD offset = cbStruct;

    // LogonDomainName
    if (cbDomain)
    {
        CopyMemory(blob + offset, kil.LogonDomainName.Buffer, kil.LogonDomainName.Length);
        pKil.LogonDomainName.Buffer = reinterpret_cast<PWSTR>(static_cast<ULONG_PTR>(offset));
        offset += cbDomain;
    }
    else
    {
        pKil.LogonDomainName.Buffer = nullptr;
    }

    // UserName
    if (cbUser)
    {
        CopyMemory(blob + offset, kil.UserName.Buffer, kil.UserName.Length);
        pKil.UserName.Buffer = reinterpret_cast<PWSTR>(static_cast<ULONG_PTR>(offset));
        offset += cbUser;
    }
    else
    {
        pKil.UserName.Buffer = nullptr;
    }

    // Password
    if (cbPass)
    {
        CopyMemory(blob + offset, kil.Password.Buffer, kil.Password.Length);
        pKil.Password.Buffer = reinterpret_cast<PWSTR>(static_cast<ULONG_PTR>(offset));
        offset += cbPass;
    }
    else
    {
        pKil.Password.Buffer = nullptr;
    }

    *ppPackedBlob  = blob;
    *pcbPackedBlob = cbTotal;
    return S_OK;
}

// ── public entry point ────────────────────────────────────────────────────────

HRESULT PackUsernamePasswordForWindows(
    const std::wstring&                        username,
    const std::wstring&                        password,
    CLSID                                      providerClsid,
    CREDENTIAL_PROVIDER_USAGE_SCENARIO         usageScenario,
    CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* serialization)
{
    if (!serialization)
        return E_POINTER;

    ZeroMemory(serialization, sizeof(*serialization));

    if (username.empty())
        return E_INVALIDARG;

    // 1. Resolve auth package.
    ULONG authPackage = 0;
    HRESULT hr = GetNegotiateAuthPackageId(&authPackage);
    if (FAILED(hr))
        return hr;

    // 2. Split "domain\user" or default to COMPUTERNAME.
    std::wstring domain, user;
    SplitOrDefaultDomain(username, domain, user);

    // 3. Build the logon structure (password used as-is; LSA handles it).
    KERB_INTERACTIVE_UNLOCK_LOGON kiul{};
    KerbInteractiveUnlockLogonInit(domain, user, password, usageScenario, kiul);

    // 4. Serialise into a flat blob.
    BYTE*  pBlob  = nullptr;
    DWORD  cbBlob = 0;
    hr = KerbInteractiveUnlockLogonPack(kiul, &pBlob, &cbBlob);

    if (FAILED(hr))
        return hr;

    serialization->ulAuthenticationPackage = authPackage;
    serialization->clsidCredentialProvider  = providerClsid;
    serialization->cbSerialization          = cbBlob;
    serialization->rgbSerialization         = pBlob;

    return S_OK;
}