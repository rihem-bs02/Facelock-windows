#pragma once

#include "Common.h"

HRESULT PackUsernamePasswordForWindows(
    const std::wstring& username,
    const std::wstring& password,
    CLSID providerClsid,
    CREDENTIAL_PROVIDER_USAGE_SCENARIO usageScenario,
    CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* serialization
);