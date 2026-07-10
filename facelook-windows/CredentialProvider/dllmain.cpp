#include "Common.h"

#include "ClassFactory.h"
#include "Guid.h"

#include <string>

HINSTANCE g_hInst = nullptr;
long g_cDllRef = 0;

static std::wstring GuidToString(REFGUID guid)
{
    wchar_t buffer[64] = {};
    StringFromGUID2(guid, buffer, ARRAYSIZE(buffer));
    return std::wstring(buffer);
}

static HRESULT SetRegistryString(
    HKEY root,
    const std::wstring& subkey,
    const std::wstring& name,
    const std::wstring& value
)
{
    HKEY key = nullptr;

    LSTATUS status = RegCreateKeyExW(
        root,
        subkey.c_str(),
        0,
        nullptr,
        REG_OPTION_NON_VOLATILE,
        KEY_WRITE,
        nullptr,
        &key,
        nullptr
    );

    if (status != ERROR_SUCCESS)
    {
        return HRESULT_FROM_WIN32(status);
    }

    status = RegSetValueExW(
        key,
        name.empty() ? nullptr : name.c_str(),
        0,
        REG_SZ,
        reinterpret_cast<const BYTE*>(value.c_str()),
        static_cast<DWORD>((value.size() + 1) * sizeof(wchar_t))
    );

    RegCloseKey(key);

    return HRESULT_FROM_WIN32(status);
}

static HRESULT RegisterProvider()
{
    wchar_t modulePath[MAX_PATH] = {};

    if (!GetModuleFileNameW(g_hInst, modulePath, ARRAYSIZE(modulePath)))
    {
        return HRESULT_FROM_WIN32(GetLastError());
    }

    const std::wstring clsidString = GuidToString(CLSID_FaceLookCredentialProvider);

    const std::wstring clsidKey =
        L"CLSID\\" + clsidString;

    const std::wstring inprocKey =
        clsidKey + L"\\InprocServer32";

    HRESULT hr = SetRegistryString(
        HKEY_CLASSES_ROOT,
        clsidKey,
        L"",
        L"FACELOOK Credential Provider"
    );

    if (FAILED(hr))
    {
        return hr;
    }

    hr = SetRegistryString(
        HKEY_CLASSES_ROOT,
        inprocKey,
        L"",
        modulePath
    );

    if (FAILED(hr))
    {
        return hr;
    }

    hr = SetRegistryString(
        HKEY_CLASSES_ROOT,
        inprocKey,
        L"ThreadingModel",
        L"Apartment"
    );

    if (FAILED(hr))
    {
        return hr;
    }

    const std::wstring providerKey =
        L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\" + clsidString;

    hr = SetRegistryString(
        HKEY_LOCAL_MACHINE,
        providerKey,
        L"",
        L"FACELOOK Credential Provider"
    );

    return hr;
}

static HRESULT DeleteRegistryTreeSafe(HKEY root, const std::wstring& subkey)
{
    const LSTATUS status = RegDeleteTreeW(root, subkey.c_str());

    if (status == ERROR_FILE_NOT_FOUND)
    {
        return S_OK;
    }

    return HRESULT_FROM_WIN32(status);
}

static HRESULT UnregisterProvider()
{
    const std::wstring clsidString = GuidToString(CLSID_FaceLookCredentialProvider);

    const std::wstring providerKey =
        L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\" + clsidString;

    DeleteRegistryTreeSafe(HKEY_LOCAL_MACHINE, providerKey);

    const std::wstring clsidKey =
        L"CLSID\\" + clsidString;

    DeleteRegistryTreeSafe(HKEY_CLASSES_ROOT, clsidKey);

    return S_OK;
}

BOOL APIENTRY DllMain(
    HMODULE hModule,
    DWORD ulReasonForCall,
    LPVOID lpReserved
)
{
    UNREFERENCED_PARAMETER(lpReserved);

    if (ulReasonForCall == DLL_PROCESS_ATTACH)
    {
        g_hInst = hModule;
        DisableThreadLibraryCalls(hModule);
    }

    return TRUE;
}

STDAPI DllCanUnloadNow()
{
    return g_cDllRef == 0 ? S_OK : S_FALSE;
}

STDAPI DllGetClassObject(
    REFCLSID rclsid,
    REFIID riid,
    LPVOID* ppv
)
{
    if (!ppv)
    {
        return E_POINTER;
    }

    *ppv = nullptr;

    if (rclsid != CLSID_FaceLookCredentialProvider)
    {
        return CLASS_E_CLASSNOTAVAILABLE;
    }

    CClassFactory* factory = new (std::nothrow) CClassFactory();

    if (!factory)
    {
        return E_OUTOFMEMORY;
    }

    HRESULT hr = factory->QueryInterface(riid, ppv);
    factory->Release();

    return hr;
}

STDAPI DllRegisterServer()
{
    return RegisterProvider();
}

STDAPI DllUnregisterServer()
{
    return UnregisterProvider();
}