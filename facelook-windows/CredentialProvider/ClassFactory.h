#pragma once

#include "Common.h"

class CClassFactory final : public IClassFactory
{
public:
    CClassFactory();
    virtual ~CClassFactory();

    IFACEMETHODIMP QueryInterface(REFIID riid, void** ppv) override;
    IFACEMETHODIMP_(ULONG) AddRef() override;
    IFACEMETHODIMP_(ULONG) Release() override;

    IFACEMETHODIMP CreateInstance(
        IUnknown* pUnkOuter,
        REFIID riid,
        void** ppv
    ) override;

    IFACEMETHODIMP LockServer(BOOL fLock) override;

private:
    long _refCount;
};