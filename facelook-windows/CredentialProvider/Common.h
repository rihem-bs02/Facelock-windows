#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

//
// Required before including sspi.h
//
#ifndef SECURITY_WIN32
#define SECURITY_WIN32
#endif

#include <windows.h>
#include <credentialprovider.h>
#include <wincred.h>
#include <sspi.h>
#include <strsafe.h>

#include <string>
#include <new>

//
// Global DLL variables
//
extern HINSTANCE g_hInst;
extern long g_cDllRef;

//
// Safe COM release helper
//
template <class T>
void SafeRelease(T** ppT)
{
    if (ppT && *ppT)
    {
        (*ppT)->Release();
        *ppT = nullptr;
    }
}

//
// Allocate PWSTR using CoTaskMemAlloc
// Caller must free with CoTaskMemFree
//
inline HRESULT AllocString(PCWSTR source, PWSTR* target)
{
    if (!target)
    {
        return E_POINTER;
    }

    *target = nullptr;

    //
    // Allow null input
    //
    if (!source)
    {
        return S_OK;
    }

    const size_t chars = wcslen(source) + 1;
    const size_t bytes = chars * sizeof(wchar_t);

    PWSTR copy = static_cast<PWSTR>(CoTaskMemAlloc(bytes));

    if (!copy)
    {
        return E_OUTOFMEMORY;
    }

    HRESULT hr = StringCchCopyW(copy, chars, source);

    if (FAILED(hr))
    {
        CoTaskMemFree(copy);
        return hr;
    }

    *target = copy;

    return S_OK;
}

//
// std::wstring overload
//
inline HRESULT AllocString(const std::wstring& source, PWSTR* target)
{
    return AllocString(source.c_str(), target);
}

//
// Securely clear sensitive strings
//
inline void SecureClearString(std::wstring& value)
{
    if (!value.empty())
    {
        SecureZeroMemory(value.data(), value.size() * sizeof(wchar_t));
        value.clear();
        value.shrink_to_fit();
    }
}

//
// Zero memory helper
//
template<typename T>
inline void SecureClearStruct(T& data)
{
    SecureZeroMemory(&data, sizeof(T));
}

//
// HRESULT helper
//
inline bool IsSuccess(HRESULT hr)
{
    return SUCCEEDED(hr);
}

//
// HRESULT helper
//
inline bool IsFailure(HRESULT hr)
{
    return FAILED(hr);
}