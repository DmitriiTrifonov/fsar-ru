// melonds-ctl: headless melonDS 1.1 driver for scripted testing (line protocol on stdin/stdout).
// Commands (one per line, replies start with "OK" or "ERR"):
//   load_rom <rom.nds> [save.sav]     boot the ROM (direct boot, FreeBIOS, English firmware, software renderer)
//   run <frames>                      run N frames without speed limit
//   keys <hex>                        set pressed buttons (A=1 B=2 Select=4 Start=8 Right=10 Left=20 Up=40 Down=80 R=100 L=200 X=400 Y=800)
//   touch <x> <y> / release           stylus
//   shot <file.ppm>                   write both screens (256x384 RGB: top over bottom)
//   save_state <file> / load_state <file>
//   read9 <addr hex> <len>            hex dump of ARM9 bus memory
//   find <text>                       search main RAM (ARM9 bus 0x02000000..0x02400000) for UTF-16LE text; prints addresses
//   quit
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdarg>
#include <chrono>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <vector>

#include "NDS.h"
#include "NDSCart.h"
#include "Platform.h"
#include "Savestate.h"
#include "SPI_Firmware.h"
#include "Args.h"

using namespace melonDS;

namespace melonDS::Platform
{
struct FileHandle { FILE* f; };
struct Thread { std::thread t; };
struct Semaphore { std::mutex m; std::condition_variable cv; int n = 0; };
struct Mutex { std::mutex m; };
struct AACDecoder {};
struct DynamicLibrary {};

void SignalStop(StopReason, void*) {}
std::string GetLocalFilePath(const std::string& filename) { return filename; }
FileHandle* OpenFile(const std::string& path, FileMode mode)
{
    std::string m;
    bool r = mode & FileMode::Read, w = mode & FileMode::Write;
    if (r && w) m = (mode & FileMode::Preserve) ? "r+" : "w+"; else if (w) m = "w"; else m = "r";
    if ((mode & FileMode::Write) && (mode & FileMode::Preserve) && !(mode & FileMode::NoCreate)) { FILE* t = fopen(path.c_str(), "a"); if (t) fclose(t); }
    FILE* f = fopen(path.c_str(), (m + "b").c_str());
    return f ? new FileHandle{f} : nullptr;
}
FileHandle* OpenLocalFile(const std::string& path, FileMode mode) { return OpenFile(path, mode); }
bool FileExists(const std::string& n) { FILE* f = fopen(n.c_str(), "rb"); if (f) fclose(f); return f != nullptr; }
bool LocalFileExists(const std::string& n) { return FileExists(n); }
bool CheckFileWritable(const std::string&) { return false; }
bool CheckLocalFileWritable(const std::string&) { return false; }
bool CloseFile(FileHandle* h) { if (!h) return false; fclose(h->f); delete h; return true; }
bool IsEndOfFile(FileHandle* h) { return feof(h->f); }
bool FileReadLine(char* s, int c, FileHandle* h) { return fgets(s, c, h->f) != nullptr; }
u64 FilePosition(FileHandle* h) { return ftell(h->f); }
bool FileSeek(FileHandle* h, s64 off, FileSeekOrigin o) { return fseek(h->f, off, o == FileSeekOrigin::Start ? SEEK_SET : o == FileSeekOrigin::Current ? SEEK_CUR : SEEK_END) == 0; }
void FileRewind(FileHandle* h) { rewind(h->f); }
u64 FileRead(void* d, u64 s, u64 c, FileHandle* h) { return fread(d, s, c, h->f); }
bool FileFlush(FileHandle* h) { return fflush(h->f) == 0; }
u64 FileWrite(const void* d, u64 s, u64 c, FileHandle* h) { return fwrite(d, s, c, h->f); }
u64 FileWriteFormatted(FileHandle* h, const char* fmt, ...) { va_list a; va_start(a, fmt); int r = vfprintf(h->f, fmt, a); va_end(a); return r; }
u64 FileLength(FileHandle* h) { long p = ftell(h->f); fseek(h->f, 0, SEEK_END); long l = ftell(h->f); fseek(h->f, p, SEEK_SET); return l; }
void Log(LogLevel, const char*, ...) {}
Thread* Thread_Create(std::function<void()> f) { return new Thread{std::thread(f)}; }
void Thread_Free(Thread* t) { if (t->t.joinable()) t->t.join(); delete t; }
void Thread_Wait(Thread* t) { if (t->t.joinable()) t->t.join(); }
Semaphore* Semaphore_Create() { return new Semaphore; }
void Semaphore_Free(Semaphore* s) { delete s; }
void Semaphore_Reset(Semaphore* s) { std::lock_guard<std::mutex> l(s->m); s->n = 0; }
void Semaphore_Wait(Semaphore* s) { std::unique_lock<std::mutex> l(s->m); s->cv.wait(l, [&] { return s->n > 0; }); s->n--; }
bool Semaphore_TryWait(Semaphore* s, int ms)
{
    std::unique_lock<std::mutex> l(s->m);
    if (!s->cv.wait_for(l, std::chrono::milliseconds(ms), [&] { return s->n > 0; })) return false;
    s->n--; return true;
}
void Semaphore_Post(Semaphore* s, int c) { { std::lock_guard<std::mutex> l(s->m); s->n += c; } s->cv.notify_all(); }
Mutex* Mutex_Create() { return new Mutex; }
void Mutex_Free(Mutex* m) { delete m; }
void Mutex_Lock(Mutex* m) { m->m.lock(); }
void Mutex_Unlock(Mutex* m) { m->m.unlock(); }
bool Mutex_TryLock(Mutex* m) { return m->m.try_lock(); }
void Sleep(u64 us) { std::this_thread::sleep_for(std::chrono::microseconds(us)); }
u64 GetMSCount() { return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
u64 GetUSCount() { return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
void WriteNDSSave(const u8*, u32, u32, u32, void*) {}
void WriteGBASave(const u8*, u32, u32, u32, void*) {}
void WriteFirmware(const Firmware&, u32, u32, void*) {}
void WriteDateTime(int, int, int, int, int, int, void*) {}
void MP_Begin(void*) {}
void MP_End(void*) {}
int MP_SendPacket(u8*, int, u64, void*) { return 0; }
int MP_RecvPacket(u8*, u64*, void*) { return 0; }
int MP_SendCmd(u8*, int, u64, void*) { return 0; }
int MP_SendReply(u8*, int, u64, u16, void*) { return 0; }
int MP_SendAck(u8*, int, u64, void*) { return 0; }
int MP_RecvHostPacket(u8*, u64*, void*) { return -1; }
u16 MP_RecvReplies(u8*, u64, u16, void*) { return 0; }
int Net_SendPacket(u8*, int, void*) { return 0; }
int Net_RecvPacket(u8*, void*) { return 0; }
void Camera_Start(int, void*) {}
void Camera_Stop(int, void*) {}
void Camera_CaptureFrame(int, u32*, int, int, bool, void*) {}
void Mic_Start(void*) {}
void Mic_Stop(void*) {}
int Mic_ReadInput(s16* d, int n, void*) { memset(d, 0, n * sizeof(s16)); return n; }
AACDecoder* AAC_Init() { return nullptr; }
void AAC_DeInit(AACDecoder*) {}
bool AAC_Configure(AACDecoder*, int, int) { return false; }
bool AAC_DecodeFrame(AACDecoder*, const void*, int, void*, int) { return false; }
bool Addon_KeyDown(KeyType, void*) { return false; }
void Addon_RumbleStart(u32, void*) {}
void Addon_RumbleStop(void*) {}
float Addon_MotionQuery(MotionQueryType, void*) { return 0; }
DynamicLibrary* DynamicLibrary_Load(const char*) { return nullptr; }
void DynamicLibrary_Unload(DynamicLibrary*) {}
void* DynamicLibrary_LoadFunction(DynamicLibrary*, const char*) { return nullptr; }
}

static std::unique_ptr<NDS> nds;
static u32 keymask = 0xFFF;

static std::vector<u8> readFile(const std::string& p)
{
    std::ifstream f(p, std::ios::binary); return std::vector<u8>((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

int main()
{
    std::string line;
    while (std::getline(std::cin, line))
    {
        std::istringstream in(line); std::string cmd; in >> cmd;
        if (cmd.empty()) continue;
        if (cmd == "quit") break;
        if (cmd == "load_rom")
        {
            std::string rom, sav; in >> rom >> sav;
            auto data = readFile(rom);
            if (data.empty()) { puts("ERR cannot read rom"); fflush(stdout); continue; }
            NDSArgs args; args.JIT = std::nullopt; args.GDB = std::nullopt;
            nds = std::make_unique<NDS>(std::move(args), nullptr);
            auto cart = NDSCart::ParseROM(data.data(), data.size(), nullptr, {});
            if (!cart) { puts("ERR rom parse failed"); fflush(stdout); continue; }
            nds->SetNDSCart(std::move(cart));
            if (!sav.empty()) { auto s = readFile(sav); if (!s.empty()) nds->SetNDSSave(s.data(), s.size()); }
            nds->Reset();
            nds->SetupDirectBoot(rom.substr(rom.find_last_of('/') + 1));
            nds->Start();
            puts("OK loaded"); fflush(stdout);
        }
        else if (!nds) { puts("ERR no rom loaded"); fflush(stdout); }
        else if (cmd == "run")
        {
            int n = 0; in >> n; auto t0 = std::chrono::steady_clock::now();
            for (int i = 0; i < n; i++) nds->RunFrame();
            double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            printf("OK %d frames in %.3f s (%.0f fps)\n", n, sec, n / (sec > 0 ? sec : 1e-9)); fflush(stdout);
        }
        else if (cmd == "keys") { unsigned m = 0; in >> std::hex >> m; keymask = (~m) & 0xFFF; nds->SetKeyMask(keymask); puts("OK"); fflush(stdout); }
        else if (cmd == "touch") { int x, y; in >> x >> y; nds->TouchScreen(x, y); puts("OK"); fflush(stdout); }
        else if (cmd == "release") { nds->ReleaseScreen(); puts("OK"); fflush(stdout); }
        else if (cmd == "shot")
        {
            std::string path; in >> path; FILE* f = fopen(path.c_str(), "wb");
            if (!f) { puts("ERR cannot open"); fflush(stdout); continue; }
            fprintf(f, "P6\n256 384\n255\n");
            int fb = nds->GPU.FrontBuffer;
            for (int s = 0; s < 2; s++)
            {
                const u32* p = nds->GPU.Framebuffer[fb][s].get();
                for (int i = 0; i < 256 * 192; i++) { u32 c = p[i]; fputc((c >> 16) & 0xFF, f); fputc((c >> 8) & 0xFF, f); fputc(c & 0xFF, f); }
            }
            fclose(f); puts("OK"); fflush(stdout);
        }
        else if (cmd == "save_state")
        {
            std::string path; in >> path; Savestate st; nds->DoSavestate(&st);
            FILE* f = fopen(path.c_str(), "wb"); if (!f || st.Error) { puts("ERR"); fflush(stdout); continue; }
            fwrite(st.Buffer(), 1, st.Length(), f); fclose(f); puts("OK"); fflush(stdout);
        }
        else if (cmd == "load_state")
        {
            std::string path; in >> path; auto buf = readFile(path);
            if (buf.empty()) { puts("ERR cannot read state"); fflush(stdout); continue; }
            Savestate st(buf.data(), (u32)buf.size(), false);
            if (!nds->DoSavestate(&st) || st.Error) { puts("ERR state load failed"); fflush(stdout); continue; }
            puts("OK"); fflush(stdout);
        }
        else if (cmd == "read9")
        {
            unsigned addr = 0, len = 0; in >> std::hex >> addr >> std::dec >> len; printf("OK ");
            for (unsigned i = 0; i < len; i++) printf("%02x", nds->ARM9Read8(addr + i));
            puts(""); fflush(stdout);
        }
        else if (cmd == "find")
        {
            std::string text; std::getline(in, text); if (!text.empty() && text[0] == ' ') text.erase(0, 1);
            std::vector<u8> pat; for (unsigned char c : text) { pat.push_back(c); pat.push_back(0); }
            std::vector<u8> ram(0x400000); for (u32 i = 0; i < ram.size(); i++) ram[i] = nds->ARM9Read8(0x02000000 + i);
            printf("OK"); int found = 0;
            for (size_t i = 0; i + pat.size() <= ram.size() && found < 20; i++)
                if (!memcmp(&ram[i], pat.data(), pat.size())) { printf(" %08zx", 0x02000000 + i); found++; }
            puts(""); fflush(stdout);
        }
        else { puts("ERR unknown command"); fflush(stdout); }
    }
    return 0;
}
