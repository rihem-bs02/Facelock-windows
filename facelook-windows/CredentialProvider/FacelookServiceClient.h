#pragma once

#include "Common.h"

struct FaceLookAuthResult
{
    bool transportOk = false;
    bool authenticated = false;
    double confidence = 0.0;
    std::wstring reason;
    std::wstring rawResponse;
};

class FaceLookServiceClient
{
public:
    FaceLookServiceClient();

    FaceLookAuthResult AuthenticateFace(
        const std::wstring& username,
        const std::wstring& host = L"127.0.0.1",
        unsigned short port = 8765,
        int timeoutMs = 15000
    );

private:
    static std::string WideToUtf8(const std::wstring& value);
    static std::wstring Utf8ToWide(const std::string& value);
    static std::string JsonEscape(const std::string& value);
    static bool ContainsJsonStringValue(
        const std::string& json,
        const std::string& key,
        const std::string& expectedValue
    );
    static std::wstring ExtractJsonStringValue(
        const std::string& json,
        const std::string& key
    );
};