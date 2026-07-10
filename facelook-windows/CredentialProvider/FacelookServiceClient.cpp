#include "FacelookServiceClient.h"

#include <winsock2.h>
#include <ws2tcpip.h>
#include <string>
#include <vector>

FaceLookServiceClient::FaceLookServiceClient()
{
}

std::string FaceLookServiceClient::WideToUtf8(const std::wstring& value)
{
    if (value.empty())
    {
        return {};
    }

    const int needed = WideCharToMultiByte(
        CP_UTF8,
        0,
        value.c_str(),
        -1,
        nullptr,
        0,
        nullptr,
        nullptr
    );

    if (needed <= 0)
    {
        return {};
    }

    std::string result(static_cast<size_t>(needed - 1), '\0');

    WideCharToMultiByte(
        CP_UTF8,
        0,
        value.c_str(),
        -1,
        result.data(),
        needed,
        nullptr,
        nullptr
    );

    return result;
}

std::wstring FaceLookServiceClient::Utf8ToWide(const std::string& value)
{
    if (value.empty())
    {
        return {};
    }

    const int needed = MultiByteToWideChar(
        CP_UTF8,
        0,
        value.c_str(),
        -1,
        nullptr,
        0
    );

    if (needed <= 0)
    {
        return {};
    }

    std::wstring result(static_cast<size_t>(needed - 1), L'\0');

    MultiByteToWideChar(
        CP_UTF8,
        0,
        value.c_str(),
        -1,
        result.data(),
        needed
    );

    return result;
}

std::string FaceLookServiceClient::JsonEscape(const std::string& value)
{
    std::string out;
    out.reserve(value.size());

    for (char ch : value)
    {
        switch (ch)
        {
        case '\\':
            out += "\\\\";
            break;
        case '"':
            out += "\\\"";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            out += ch;
            break;
        }
    }

    return out;
}

bool FaceLookServiceClient::ContainsJsonStringValue(
    const std::string& json,
    const std::string& key,
    const std::string& expectedValue
)
{
    const std::string compactPattern =
        "\"" + key + "\":\"" + expectedValue + "\"";

    if (json.find(compactPattern) != std::string::npos)
    {
        return true;
    }

    const std::string looseKey = "\"" + key + "\"";
    const size_t keyPos = json.find(looseKey);
    if (keyPos == std::string::npos)
    {
        return false;
    }

    const size_t expectedPos = json.find("\"" + expectedValue + "\"", keyPos);
    return expectedPos != std::string::npos;
}

std::wstring FaceLookServiceClient::ExtractJsonStringValue(
    const std::string& json,
    const std::string& key
)
{
    const std::string keyPattern = "\"" + key + "\"";
    const size_t keyPos = json.find(keyPattern);

    if (keyPos == std::string::npos)
    {
        return L"";
    }

    const size_t colonPos = json.find(':', keyPos + keyPattern.size());
    if (colonPos == std::string::npos)
    {
        return L"";
    }

    const size_t firstQuote = json.find('"', colonPos + 1);
    if (firstQuote == std::string::npos)
    {
        return L"";
    }

    const size_t secondQuote = json.find('"', firstQuote + 1);
    if (secondQuote == std::string::npos)
    {
        return L"";
    }

    const std::string value = json.substr(
        firstQuote + 1,
        secondQuote - firstQuote - 1
    );

    return Utf8ToWide(value);
}

FaceLookAuthResult FaceLookServiceClient::AuthenticateFace(
    const std::wstring& username,
    const std::wstring& host,
    unsigned short port,
    int timeoutMs
)
{
    FaceLookAuthResult result;

    WSADATA wsaData = {};
    const int wsa = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (wsa != 0)
    {
        result.reason = L"WINSOCK_STARTUP_FAILED";
        return result;
    }

    SOCKET sock = INVALID_SOCKET;

    do
    {
        sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock == INVALID_SOCKET)
        {
            result.reason = L"SOCKET_CREATE_FAILED";
            break;
        }

        DWORD timeout = static_cast<DWORD>(timeoutMs);
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&timeout), sizeof(timeout));
        setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, reinterpret_cast<const char*>(&timeout), sizeof(timeout));

        sockaddr_in addr = {};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);

        const std::string hostUtf8 = WideToUtf8(host);

        if (inet_pton(AF_INET, hostUtf8.c_str(), &addr.sin_addr) != 1)
        {
            result.reason = L"INVALID_SERVICE_HOST";
            break;
        }

        if (connect(sock, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == SOCKET_ERROR)
        {
            result.reason = L"FACELOOK_SERVICE_CONNECT_FAILED";
            break;
        }

        const std::string userUtf8 = WideToUtf8(username);

        const std::string request =
            "{\"version\":1,"
            "\"request\":\"AUTHENTICATE_FACE\","
            "\"username\":\"" + JsonEscape(userUtf8) + "\"}\n";

        const int sent = send(
            sock,
            request.c_str(),
            static_cast<int>(request.size()),
            0
        );

        if (sent == SOCKET_ERROR)
        {
            result.reason = L"FACELOOK_SERVICE_SEND_FAILED";
            break;
        }

        std::string response;
        char buffer[4096] = {};

        while (true)
        {
            const int received = recv(sock, buffer, sizeof(buffer) - 1, 0);

            if (received == SOCKET_ERROR)
            {
                result.reason = L"FACELOOK_SERVICE_RECV_FAILED";
                break;
            }

            if (received == 0)
            {
                break;
            }

            buffer[received] = '\0';
            response.append(buffer, static_cast<size_t>(received));

            if (response.find('\n') != std::string::npos)
            {
                break;
            }

            if (response.size() > 8192)
            {
                result.reason = L"FACELOOK_RESPONSE_TOO_LARGE";
                break;
            }
        }

        if (response.empty())
        {
            result.reason = L"FACELOOK_EMPTY_RESPONSE";
            break;
        }

        result.transportOk = true;
        result.rawResponse = Utf8ToWide(response);

        if (ContainsJsonStringValue(response, "result", "AUTH_OK"))
        {
            result.authenticated = true;
            result.reason = ExtractJsonStringValue(response, "reason");
            if (result.reason.empty())
            {
                result.reason = L"AUTH_OK";
            }
        }
        else
        {
            result.authenticated = false;
            result.reason = ExtractJsonStringValue(response, "reason");
            if (result.reason.empty())
            {
                result.reason = L"AUTH_DENIED";
            }
        }

    } while (false);

    if (sock != INVALID_SOCKET)
    {
        closesocket(sock);
    }

    WSACleanup();
    return result;
}