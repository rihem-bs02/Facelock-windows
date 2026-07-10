#include "ClassFactory.h"

#include "FacelookProvider.h"

CClassFactory::CClassFactory()
    : _refCount(1)
{
    InterlockedIncrement(&g_cDllRef);
}

CClassFactory::~CClassFactory()
{
    InterlockedDecrement(&g_cDllRef);
}

IFACEMETHODIMP CClassFactory::QueryInterface(REFIID riid, void** ppv)
{
    if (!ppv)
    {
        return E_POINTER;
    }

    *ppv = nullptr;

    if (riid == IID_IUnknown || riid == IID_IClassFactory)
    {
        *ppv = static_cast<IClassFactory*>(this);
        AddRef();
        return S_OK;
    }

    return E_NOINTERFACE;
}

IFACEMETHODIMP_(ULONG) CClassFactory::AddRef()
{
    return static_cast<ULONG>(InterlockedIncrement(&_refCount));
}

IFACEMETHODIMP_(ULONG) CClassFactory::Release()
{
    const long count = InterlockedDecrement(&_refCount);

    if (count == 0)
    {
        delete this;
    }

    return static_cast<ULONG>(count);
}

IFACEMETHODIMP CClassFactory::CreateInstance(
    IUnknown* pUnkOuter,
    REFIID riid,
    void** ppv
)
{
    if (!ppv)
    {
        return E_POINTER;
    }

    *ppv = nullptr;

    if (pUnkOuter)
    {
        return CLASS_E_NOAGGREGATION;
    }

    CFacelookProvider* provider = new (std::nothrow) CFacelookProvider();

    if (!provider)
    {
        return E_OUTOFMEMORY;
    }

    HRESULT hr = provider->QueryInterface(riid, ppv);
    provider->Release();

    return hr;
}

IFACEMETHODIMP CClassFactory::LockServer(BOOL fLock)
{
    if (fLock)
    {
        InterlockedIncrement(&g_cDllRef);
    }
    else
    {
        InterlockedDecrement(&g_cDllRef);
    }

    return S_OK;
}