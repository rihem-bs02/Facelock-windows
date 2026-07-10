#include "FacelookCredential.h"

#include "FacelookServiceClient.h"
#include "SerializationHelpers.h"
#include "Guid.h"

//
// Field state (UI visibility)
//
static const CREDENTIAL_PROVIDER_FIELD_STATE g_FieldState[FID_NUM_FIELDS] =
{
    CPFS_DISPLAY_IN_BOTH,          // FID_TILEIMAGE
    CPFS_DISPLAY_IN_BOTH,          // FID_TITLE
    CPFS_DISPLAY_IN_SELECTED_TILE, // FID_INSTRUCTION
    CPFS_DISPLAY_IN_SELECTED_TILE, // FID_USERNAME
    CPFS_DISPLAY_IN_SELECTED_TILE, // FID_FACE_STATUS
    CPFS_DISPLAY_IN_SELECTED_TILE, // FID_FACE_BUTTON
    CPFS_DISPLAY_IN_SELECTED_TILE  // FID_SUBMIT_BUTTON
};

//
// Interactive state (IMPORTANT FIX HERE)
// CPFIS_ENABLED does NOT exist → replaced with CPFIS_FOCUSED / CPFIS_NONE
//
static const CREDENTIAL_PROVIDER_FIELD_INTERACTIVE_STATE g_FieldInteractiveState[FID_NUM_FIELDS] =
{
    CPFIS_NONE,    // FID_TILEIMAGE
    CPFIS_NONE,    // FID_TITLE
    CPFIS_NONE,    // FID_INSTRUCTION
    CPFIS_FOCUSED, // FID_USERNAME
    CPFIS_NONE,    // FID_FACE_STATUS
    CPFIS_NONE,    // FID_FACE_BUTTON
    CPFIS_NONE     // FID_SUBMIT_BUTTON
};

//
// Constructor
//
CFacelookCredential::CFacelookCredential(
    CREDENTIAL_PROVIDER_USAGE_SCENARIO usageScenario
)
    : _refCount(1),
      _events(nullptr),
      _usageScenario(usageScenario),
      _status(L"Enter your username, then verify your face."),
      _faceVerified(false)
{
    InterlockedIncrement(&g_cDllRef);
}

//
// Destructor
//
CFacelookCredential::~CFacelookCredential()
{
    SafeRelease(&_events);

    SecureClearString(_username);
    SecureClearString(_status);

    InterlockedDecrement(&g_cDllRef);
}

//
// QueryInterface
//
IFACEMETHODIMP CFacelookCredential::QueryInterface(REFIID riid, void** ppv)
{
    if (!ppv)
        return E_POINTER;

    *ppv = nullptr;

    if (riid == IID_IUnknown ||
        riid == IID_ICredentialProviderCredential ||
        riid == IID_ICredentialProviderCredential2)
    {
        *ppv = static_cast<ICredentialProviderCredential2*>(this);
        AddRef();
        return S_OK;
    }

    return E_NOINTERFACE;
}

//
// AddRef
//
IFACEMETHODIMP_(ULONG) CFacelookCredential::AddRef()
{
    return static_cast<ULONG>(InterlockedIncrement(&_refCount));
}

//
// Release
//
IFACEMETHODIMP_(ULONG) CFacelookCredential::Release()
{
    long count = InterlockedDecrement(&_refCount);

    if (count == 0)
        delete this;

    return static_cast<ULONG>(count);
}

//
// Advise
//
IFACEMETHODIMP CFacelookCredential::Advise(ICredentialProviderCredentialEvents* pcpce)
{
    SafeRelease(&_events);

    if (pcpce)
    {
        _events = pcpce;
        _events->AddRef();
    }

    return S_OK;
}

//
// UnAdvise
//
IFACEMETHODIMP CFacelookCredential::UnAdvise()
{
    SafeRelease(&_events);
    return S_OK;
}

//
// Selected
//
IFACEMETHODIMP CFacelookCredential::SetSelected(BOOL* pbAutoLogon)
{
    if (pbAutoLogon)
        *pbAutoLogon = FALSE;

    return S_OK;
}

//
// Deselected
//
IFACEMETHODIMP CFacelookCredential::SetDeselected()
{
    _faceVerified = false;
    UpdateStatus(L"Credential deselected.");
    return S_OK;
}

//
// Field state
//
IFACEMETHODIMP CFacelookCredential::GetFieldState(
    DWORD dwFieldID,
    CREDENTIAL_PROVIDER_FIELD_STATE* pcpfs,
    CREDENTIAL_PROVIDER_FIELD_INTERACTIVE_STATE* pcpfis
)
{
    if (!pcpfs || !pcpfis)
        return E_POINTER;

    if (dwFieldID >= FID_NUM_FIELDS)
        return E_INVALIDARG;

    *pcpfs = g_FieldState[dwFieldID];
    *pcpfis = g_FieldInteractiveState[dwFieldID];

    return S_OK;
}

//
// String values
//
IFACEMETHODIMP CFacelookCredential::GetStringValue(DWORD dwFieldID, PWSTR* ppwsz)
{
    if (!ppwsz)
        return E_POINTER;

    *ppwsz = nullptr;

    switch (dwFieldID)
    {
    case FID_TITLE:
        return AllocString(L"FACELOOK", ppwsz);

    case FID_INSTRUCTION:
        return AllocString(L"Biometric authentication for Windows", ppwsz);

    case FID_USERNAME:
        return AllocString(_username, ppwsz);

    case FID_FACE_STATUS:
        return AllocString(_status, ppwsz);

    case FID_FACE_BUTTON:
        return AllocString(L"Verify face with FACELOOK", ppwsz);

    case FID_SUBMIT_BUTTON:
        return AllocString(L"Sign in", ppwsz);

    default:
        return E_INVALIDARG;
    }
}

//
// Update status safely
//
void CFacelookCredential::UpdateStatus(const std::wstring& status)
{
    _status = status;

    if (_events)
    {
        _events->SetFieldString(this, FID_FACE_STATUS, _status.c_str());
    }
}

//
// Face verification
//
HRESULT CFacelookCredential::VerifyFace()
{
    if (_username.empty())
    {
        _faceVerified = false;
        UpdateStatus(L"Username is required before biometric verification.");
        return S_OK;
    }

    UpdateStatus(L"Contacting FACELOOK service...");

    FaceLookServiceClient client;
    FaceLookAuthResult result = client.AuthenticateFace(_username);

    if (!result.transportOk)
    {
        _faceVerified = false;
        UpdateStatus(L"FACELOOK service error.");
        return S_OK;
    }

    if (result.authenticated)
    {
        _faceVerified = true;
        UpdateStatus(L"Face verified. You can sign in.");
    }
    else
    {
        _faceVerified = false;
        UpdateStatus(L"Face authentication denied.");
    }

    return S_OK;
}

//
// GetBitmapValue — not used in this provider
//
IFACEMETHODIMP CFacelookCredential::GetBitmapValue(DWORD /*dwFieldID*/, HBITMAP* /*phbmp*/)
{
    return E_NOTIMPL;
}

//
// GetCheckboxValue — not used in this provider
//
IFACEMETHODIMP CFacelookCredential::GetCheckboxValue(DWORD /*dwFieldID*/, BOOL* /*pbChecked*/, PWSTR* /*ppwszLabel*/)
{
    return E_NOTIMPL;
}

//
// GetComboBoxValueCount — not used in this provider
//
IFACEMETHODIMP CFacelookCredential::GetComboBoxValueCount(DWORD /*dwFieldID*/, DWORD* /*pcItems*/, DWORD* /*pdwSelectedItem*/)
{
    return E_NOTIMPL;
}

//
// GetComboBoxValueAt — not used in this provider
//
IFACEMETHODIMP CFacelookCredential::GetComboBoxValueAt(DWORD /*dwFieldID*/, DWORD /*dwItem*/, PWSTR* /*ppwszItem*/)
{
    return E_NOTIMPL;
}

//
// GetSubmitButtonValue — returns the field adjacent to the submit button
//
IFACEMETHODIMP CFacelookCredential::GetSubmitButtonValue(DWORD dwFieldID, DWORD* pdwAdjacentTo)
{
    if (!pdwAdjacentTo)
        return E_POINTER;

    if (dwFieldID == FID_SUBMIT_BUTTON)
    {
        *pdwAdjacentTo = FID_USERNAME;
        return S_OK;
    }

    return E_INVALIDARG;
}

//
// SetStringValue — called when the user edits a text field
//
IFACEMETHODIMP CFacelookCredential::SetStringValue(DWORD dwFieldID, PCWSTR pwz)
{
    switch (dwFieldID)
    {
    case FID_USERNAME:
        _username = pwz ? pwz : L"";
        return S_OK;

    default:
        return E_INVALIDARG;
    }
}

//
// SetCheckboxValue — not used in this provider
//
IFACEMETHODIMP CFacelookCredential::SetCheckboxValue(DWORD /*dwFieldID*/, BOOL /*bChecked*/)
{
    return E_NOTIMPL;
}

//
// SetComboBoxSelectedValue — not used in this provider
//
IFACEMETHODIMP CFacelookCredential::SetComboBoxSelectedValue(DWORD /*dwFieldID*/, DWORD /*dwSelectedItem*/)
{
    return E_NOTIMPL;
}

//
// CommandLinkClicked — triggered when the user clicks the face verify button
//
IFACEMETHODIMP CFacelookCredential::CommandLinkClicked(DWORD dwFieldID)
{
    if (dwFieldID == FID_FACE_BUTTON)
    {
        return VerifyFace();
    }

    return E_INVALIDARG;
}

//
// GetSerialization — packages credentials for Windows authentication
//
IFACEMETHODIMP CFacelookCredential::GetSerialization(
    CREDENTIAL_PROVIDER_GET_SERIALIZATION_RESPONSE* pcpgsr,
    CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs,
    PWSTR* ppwszOptionalStatusText,
    CREDENTIAL_PROVIDER_STATUS_ICON* pcpsiOptionalStatusIcon
)
{
    if (!pcpgsr || !pcpcs || !ppwszOptionalStatusText || !pcpsiOptionalStatusIcon)
        return E_POINTER;

    *ppwszOptionalStatusText = nullptr;
    *pcpsiOptionalStatusIcon = CPSI_NONE;

    if (!_faceVerified)
    {
        *pcpgsr = CPGSR_NO_CREDENTIAL_FINISHED;
        AllocString(L"Face verification required before sign in.", ppwszOptionalStatusText);
        *pcpsiOptionalStatusIcon = CPSI_ERROR;
        return S_OK;
    }

    HRESULT hr = PackUsernamePasswordForWindows(
        _username,
        L"",
        CLSID_FaceLookCredentialProvider,
        _usageScenario,
        pcpcs
    );

    if (SUCCEEDED(hr))
    {
        *pcpgsr = CPGSR_RETURN_CREDENTIAL_FINISHED;
    }
    else
    {
        *pcpgsr = CPGSR_NO_CREDENTIAL_FINISHED;
        *pcpsiOptionalStatusIcon = CPSI_ERROR;
    }

    return hr;
}

//
// ReportResult — called by Windows after authentication attempt
//
IFACEMETHODIMP CFacelookCredential::ReportResult(
    NTSTATUS ntsStatus,
    NTSTATUS /*ntsSubstatus*/,
    PWSTR* ppwszOptionalStatusText,
    CREDENTIAL_PROVIDER_STATUS_ICON* pcpsiOptionalStatusIcon
)
{
    if (!ppwszOptionalStatusText || !pcpsiOptionalStatusIcon)
        return E_POINTER;

    *ppwszOptionalStatusText = nullptr;
    *pcpsiOptionalStatusIcon = CPSI_NONE;

    if (FAILED(ntsStatus))
    {
        _faceVerified = false;
        UpdateStatus(L"Authentication failed. Please retry face verification.");
    }

    return S_OK;
}

//
// GetUserSid — returns null SID (not tile-enumeration mode)
//
IFACEMETHODIMP CFacelookCredential::GetUserSid(PWSTR* ppszSid)
{
    if (!ppszSid)
        return E_POINTER;

    *ppszSid = nullptr;
    return S_OK;
}