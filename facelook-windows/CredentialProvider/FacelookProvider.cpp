#include "FacelookProvider.h"

#include "Common.h"
#include "FieldIds.h"
#include "FacelookCredential.h"

//
// Credential Provider field descriptors
//
static const CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR g_FieldDescriptors[FID_NUM_FIELDS] =
{
    //
    // Tile image
    //
    {
        FID_TILEIMAGE,
        CPFT_TILE_IMAGE,
        const_cast<PWSTR>(L""),
        GUID_NULL
    },

    //
    // Title
    //
    {
        FID_TITLE,
        CPFT_LARGE_TEXT,
        const_cast<PWSTR>(L"FACELOOK"),
        GUID_NULL
    },

    //
    // Instruction
    //
    {
        FID_INSTRUCTION,
        CPFT_SMALL_TEXT,
        const_cast<PWSTR>(L"Biometric authentication"),
        GUID_NULL
    },

    //
    // Username
    //
    {
        FID_USERNAME,
        CPFT_EDIT_TEXT,
        const_cast<PWSTR>(L"Username"),
        GUID_NULL
    },


    // Face status
    //
    {
        FID_FACE_STATUS,
        CPFT_SMALL_TEXT,
        const_cast<PWSTR>(L"Status"),
        GUID_NULL
    },

    //
    // Face verify button
    //
    {
        FID_FACE_BUTTON,
        CPFT_COMMAND_LINK,
        const_cast<PWSTR>(L"Verify face with FACELOOK"),
        GUID_NULL
    },

    //
    // Submit button
    //
    {
        FID_SUBMIT_BUTTON,
        CPFT_SUBMIT_BUTTON,
        const_cast<PWSTR>(L"Sign in"),
        GUID_NULL
    }
};

//
// Copies field descriptor using CoTaskMemAlloc
//
static HRESULT FieldDescriptorCoAllocCopy(
    const CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR& source,
    CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR** target
)
{
    if (!target)
    {
        return E_POINTER;
    }

    *target = nullptr;

    auto copy =
        static_cast<CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR*>(
            CoTaskMemAlloc(sizeof(CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR))
        );

    if (!copy)
    {
        return E_OUTOFMEMORY;
    }

    ZeroMemory(copy, sizeof(CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR));

    copy->dwFieldID = source.dwFieldID;
    copy->cpft = source.cpft;
    copy->guidFieldType = source.guidFieldType;

    HRESULT hr = AllocString(source.pszLabel, &copy->pszLabel);

    if (FAILED(hr))
    {
        CoTaskMemFree(copy);
        return hr;
    }

    *target = copy;

    return S_OK;
}

//
// Constructor
//
CFacelookProvider::CFacelookProvider() :
    _refCount(1),
    _usageScenario(CPUS_INVALID)
{
    InterlockedIncrement(&g_cDllRef);
}

//
// Destructor
//
CFacelookProvider::~CFacelookProvider()
{
    InterlockedDecrement(&g_cDllRef);
}

//
// IUnknown::QueryInterface
//
IFACEMETHODIMP CFacelookProvider::QueryInterface(
    REFIID riid,
    void** ppv
)
{
    if (!ppv)
    {
        return E_POINTER;
    }

    *ppv = nullptr;

    if (riid == IID_IUnknown ||
        riid == IID_ICredentialProvider)
    {
        *ppv = static_cast<ICredentialProvider*>(this);
        AddRef();
        return S_OK;
    }

    return E_NOINTERFACE;
}

//
// IUnknown::AddRef
//
IFACEMETHODIMP_(ULONG) CFacelookProvider::AddRef()
{
    return static_cast<ULONG>(
        InterlockedIncrement(&_refCount)
    );
}

//
// IUnknown::Release
//
IFACEMETHODIMP_(ULONG) CFacelookProvider::Release()
{
    long count = InterlockedDecrement(&_refCount);

    if (count == 0)
    {
        delete this;
    }

    return static_cast<ULONG>(count);
}

//
// Set usage scenario
//
IFACEMETHODIMP CFacelookProvider::SetUsageScenario(
    CREDENTIAL_PROVIDER_USAGE_SCENARIO cpus,
    DWORD dwFlags
)
{
    UNREFERENCED_PARAMETER(dwFlags);

    switch (cpus)
    {
    case CPUS_LOGON:
    case CPUS_UNLOCK_WORKSTATION:
        _usageScenario = cpus;
        return S_OK;

    default:
        return E_NOTIMPL;
    }
}

//
// Serialization
//
IFACEMETHODIMP CFacelookProvider::SetSerialization(
    const CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs
)
{
    UNREFERENCED_PARAMETER(pcpcs);
    return S_OK;
}

//
// Advise
//
IFACEMETHODIMP CFacelookProvider::Advise(
    ICredentialProviderEvents* pcpe,
    UINT_PTR upAdviseContext
)
{
    UNREFERENCED_PARAMETER(pcpe);
    UNREFERENCED_PARAMETER(upAdviseContext);

    return S_OK;
}

//
// UnAdvise
//
IFACEMETHODIMP CFacelookProvider::UnAdvise()
{
    return S_OK;
}

//
// Number of UI fields
//
IFACEMETHODIMP CFacelookProvider::GetFieldDescriptorCount(
    DWORD* pdwCount
)
{
    if (!pdwCount)
    {
        return E_POINTER;
    }

    *pdwCount = FID_NUM_FIELDS;

    return S_OK;
}

//
// Get field descriptor
//
IFACEMETHODIMP CFacelookProvider::GetFieldDescriptorAt(
    DWORD dwIndex,
    CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR** ppcpfd
)
{
    if (!ppcpfd)
    {
        return E_POINTER;
    }

    if (dwIndex >= FID_NUM_FIELDS)
    {
        return E_INVALIDARG;
    }

    return FieldDescriptorCoAllocCopy(
        g_FieldDescriptors[dwIndex],
        ppcpfd
    );
}

//
// Credential count
//
IFACEMETHODIMP CFacelookProvider::GetCredentialCount(
    DWORD* pdwCount,
    DWORD* pdwDefault,
    BOOL* pbAutoLogonWithDefault
)
{
    if (!pdwCount ||
        !pdwDefault ||
        !pbAutoLogonWithDefault)
    {
        return E_POINTER;
    }

    *pdwCount = 1;
    *pdwDefault = 0;
    *pbAutoLogonWithDefault = FALSE;

    return S_OK;
}

//
// Get credential object
//
IFACEMETHODIMP CFacelookProvider::GetCredentialAt(
    DWORD dwIndex,
    ICredentialProviderCredential** ppcpc
)
{
    if (!ppcpc)
    {
        return E_POINTER;
    }

    *ppcpc = nullptr;

    if (dwIndex != 0)
    {
        return E_INVALIDARG;
    }

    auto credential =
        new (std::nothrow) CFacelookCredential(_usageScenario);

    if (!credential)
    {
        return E_OUTOFMEMORY;
    }

    HRESULT hr =
        credential->QueryInterface(
            IID_ICredentialProviderCredential,
            reinterpret_cast<void**>(ppcpc)
        );

    credential->Release();

    return hr;
}