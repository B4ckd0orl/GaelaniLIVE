/*
 * gaelanilive_update.cpp - self-update: the page downloads the new release from GitHub, POSTs it
 * to /api/update, this module verifies it, swaps it in and relaunches the payload with
 * elfldr_spawn (the same loader that started it). GPL-3.0.
 *
 * Files (all in /data/GaelaniLIVE):
 *   gaelanilive.elf        the installed payload (the relaunch loads this copy)
 *   gaelanilive.elf.new    staged download, verified before it is swapped in
 *   gaelanilive.elf.bak    the previous version (rollback)
 *   update.applied         written just before the relaunch: the next run verifies the update
 *   update.booting         claimed by that run; a run that sees it at startup means the updated
 *                          payload died before it stabilized -> the .bak is restored
 */
#include "gaelanilive.hpp"

#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <pthread.h>
#include <string>
#include <unistd.h>
#include <vector>
#include <sys/stat.h>

extern "C" {
// onion/elfldr.h (declared here as in the header; the library is already linked).
pid_t elfldr_spawn(int stdio, char* const argv[], uint8_t* elf, size_t elf_size);
int   elfldr_sanity_check(uint8_t* elf, size_t elf_size);
}

namespace gaelanilive {

#ifndef GAELANILIVE_VERSION
#define GAELANILIVE_VERSION "0.0.0-dev"
#endif

namespace {

constexpr const char* kElfPath     = "/data/GaelaniLIVE/gaelanilive.elf";
constexpr const char* kElfNew      = "/data/GaelaniLIVE/gaelanilive.elf.new";
constexpr const char* kElfBak      = "/data/GaelaniLIVE/gaelanilive.elf.bak";
constexpr const char* kAppliedFile = "/data/GaelaniLIVE/update.applied";
constexpr const char* kBootingFile = "/data/GaelaniLIVE/update.booting";
constexpr const char* kPathFile    = "/system_tmp/gaelanilive/video.txt";

// True only for the run that claimed a just-installed update (update.applied -> update.booting):
// inject_shellui uses it to end ShellUI when the previous build's module is still in there.
bool g_fresh_claim = false;

bool file_exists(const std::string& path) {
	struct stat st {};
	return stat(path.c_str(), &st) == 0;
}

// ---- sha256 (FIPS 180-4; compact public-domain style implementation) --------------------------

struct Sha256 {
	uint32_t h[8] = {0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
	                 0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u};
	uint64_t len = 0;
	size_t   n   = 0;
	uint8_t  buf[64] = {};

	static uint32_t rotr(uint32_t x, int k) { return (x >> k) | (x << (32 - k)); }

	void block(const uint8_t* p) {
		static const uint32_t k[64] = {
		    0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
		    0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u, 0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
		    0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
		    0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
		    0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u, 0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
		    0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
		    0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
		    0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u, 0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u};
		uint32_t w[64];
		for (int i = 0; i < 16; ++i) {
			w[i] = (uint32_t(p[i * 4]) << 24) | (uint32_t(p[i * 4 + 1]) << 16) |
			       (uint32_t(p[i * 4 + 2]) << 8) | uint32_t(p[i * 4 + 3]);
		}
		for (int i = 16; i < 64; ++i) {
			const uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
			const uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
			w[i] = w[i - 16] + s0 + w[i - 7] + s1;
		}
		uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
		for (int i = 0; i < 64; ++i) {
			const uint32_t S1  = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
			const uint32_t ch  = (e & f) ^ (~e & g);
			const uint32_t t1  = hh + S1 + ch + k[i] + w[i];
			const uint32_t S0  = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
			const uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
			const uint32_t t2  = S0 + maj;
			hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
		}
		h[0] += a; h[1] += b; h[2] += c; h[3] += d;
		h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
	}
};

// The struct above only holds state; these two do the work (kept separate for clarity).
void sha_feed(Sha256& s, const void* data, size_t len) {
	const auto* p = static_cast<const uint8_t*>(data);
	s.len += len;
	while (len > 0) {
		const size_t take = 64 - s.n < len ? 64 - s.n : len;
		memcpy(s.buf + s.n, p, take);
		s.n += take;
		p += take;
		len -= take;
		if (s.n == 64) {
			s.block(s.buf);
			s.n = 0;
		}
	}
}

std::string sha_finish(Sha256& s) {
	const uint64_t bits = s.len * 8;
	uint8_t        pad[72];
	size_t         padlen = s.n < 56 ? 56 - s.n : 120 - s.n;
	memset(pad, 0, sizeof(pad));
	pad[0] = 0x80;
	for (int i = 0; i < 8; ++i) {
		pad[padlen + i] = static_cast<uint8_t>(bits >> (56 - i * 8));
	}
	sha_feed(s, pad, padlen + 8);
	char out[65];
	for (int i = 0; i < 8; ++i) {
		snprintf(out + i * 8, 9, "%08x", s.h[i]);
	}
	return std::string(out, 64);
}

} // namespace

const char* version() {
	return GAELANILIVE_VERSION;
}

std::string sha256_file(const std::string& path) {
	FILE* f = fopen(path.c_str(), "rb");
	if (f == nullptr) {
		return {};
	}
	Sha256 s;
	uint8_t buf[64 * 1024];
	size_t  n = 0;
	while ((n = fread(buf, 1, sizeof(buf), f)) > 0) {
		sha_feed(s, buf, n);
	}
	fclose(f);
	return sha_finish(s);
}

bool elf_bytes_ok(const std::string& path) {
	FILE* f = fopen(path.c_str(), "rb");
	if (f == nullptr) {
		return false;
	}
	uint8_t magic[4] = {};
	const bool head  = fread(magic, 1, 4, f) == 4 && magic[0] == 0x7f && magic[1] == 'E' && magic[2] == 'L' &&
	                   magic[3] == 'F';
	fclose(f);
	if (!head) {
		return false;
	}
	// Full bounds check by the loader itself.
	FILE* g = fopen(path.c_str(), "rb");
	if (g == nullptr) {
		return false;
	}
	fseek(g, 0, SEEK_END);
	const long size = ftell(g);
	fseek(g, 0, SEEK_SET);
	if (size < 64 * 1024 || size > 32L * 1024 * 1024) {
		fclose(g);
		return false;
	}
	std::vector<uint8_t> data(static_cast<size_t>(size));
	const size_t         got = fread(data.data(), 1, data.size(), g);
	fclose(g);
	return got == data.size() && elfldr_sanity_check(data.data(), data.size()) == 0;
}

std::string booting_version() {
	FILE* f = fopen(kBootingFile, "rb");
	if (f == nullptr) {
		return {};
	}
	char        buf[64] = {};
	const size_t got    = fread(buf, 1, sizeof(buf) - 1, f);
	fclose(f);
	std::string out;
	for (size_t i = 0; i < got && buf[i] != '\n' && buf[i] != '\r'; ++i) {
		out += buf[i];
	}
	return out;
}

// ---- startup: claim a fresh update, or roll back one that did not survive --------------------

void update_boot_check() {
	if (file_exists(kAppliedFile)) {
		// The run started right after the swap: claim the verification window.
		// (update.applied already carries the version tag written by install_now.)
		g_fresh_claim = true;
		unlink(kBootingFile);
		if (rename(kAppliedFile, kBootingFile) != 0) {
			unlink(kAppliedFile);
		}
		log("update: this run verifies version %s (30 s to stabilize)", GAELANILIVE_VERSION);
		return;
	}
	if (file_exists(kBootingFile)) {
		// Window still open. Same version as this binary = a reload of the very build being
		// verified (handover / manual reload): keep the window, it is not a dead update.
		if (booting_version() == GAELANILIVE_VERSION) {
			log("update: continuing the verification window of %s", GAELANILIVE_VERSION);
			return;
		}
		// Some other version died before it stabilized: go back to the previous elf.
		unlink(kBootingFile);
		const bool have_old = file_exists(kElfBak);
		if (have_old) {
			unlink(kElfPath);
			rename(kElfBak, kElfPath);
		}
		log("update: the new version did not survive; %s", have_old ? "rolled back to the previous elf" : "no backup to restore");
		notify("GaelaniLIVE: la actualización falló; se restauró la versión anterior. Vuelve a cargar el payload.");
	}
}

void update_boot_ok() {
	unlink(kBootingFile);
}

void* stabilize_thread(void*) {
	sleep(30); // 30 s without a crash marks the update as good
	if (file_exists(kBootingFile)) {
		unlink(kBootingFile);
		log("update: version %s stabilized", GAELANILIVE_VERSION);
	}
	return nullptr;
}

// Called once the payload is up.
void update_stabilize_start() {
	if (!file_exists(kBootingFile)) {
		return;
	}
	pthread_t th;
	if (pthread_create(&th, nullptr, stabilize_thread, nullptr) == 0) {
		pthread_detach(th);
	}
}

bool update_fresh_claim() {
	return g_fresh_claim;
}

// ---- install: swap the verified file in, then relaunch --------------------------------------

namespace {

void install_now(const std::string& ver) {
	// Hand the home screen back to Sony first. The injected marker stays: it tells the new run
	// (inject_shellui) which build's module is still inside ShellUI, so it can end ShellUI and
	// inject into a clean one instead of leaving two modules fighting over the video.
	{
		FILE* f = fopen(kPathFile, "w");
		if (f != nullptr) {
			fputs("off\n", f);
			fclose(f);
		}
	}
	const bool had_old = file_exists(kElfPath);
	unlink(kElfBak);
	if (had_old && rename(kElfPath, kElfBak) != 0) {
		log("update: cannot move the running elf aside (%s)", strerror(errno));
	}
	if (rename(kElfNew, kElfPath) != 0) {
		log("update: cannot move the new elf into place (%s)", strerror(errno));
		if (had_old) {
			rename(kElfBak, kElfPath); // put it back
		}
		notify("GaelaniLIVE: no se pudo colocar el elf nuevo. Registro: /data/GaelaniLIVE/gaelanilive.log");
		return;
	}
	{
		FILE* f = fopen(kAppliedFile, "w");
		if (f != nullptr) {
			fputs(ver.empty() ? "unknown" : ver.c_str(), f);
			fputc('\n', f);
			fclose(f);
		}
	}
	FILE* f = fopen(kElfPath, "rb");
	if (f == nullptr) {
		unlink(kAppliedFile);
		log("update: cannot read back %s", kElfPath);
		return;
	}
	fseek(f, 0, SEEK_END);
	const long size = ftell(f);
	fseek(f, 0, SEEK_SET);
	std::vector<uint8_t> data(size > 0 ? static_cast<size_t>(size) : 0);
	const size_t         got = size > 0 ? fread(data.data(), 1, data.size(), f) : 0;
	fclose(f);
	if (got != data.size() || elfldr_sanity_check(data.data(), data.size()) != 0) {
		unlink(kAppliedFile);
		log("update: the installed elf does not pass the loader check");
		notify("GaelaniLIVE: el elf nuevo no es válido. Registro: /data/GaelaniLIVE/gaelanilive.log");
		return;
	}
	char*        argv[2] = {const_cast<char*>("gaelanilive.elf"), nullptr};
	const pid_t  pid     = elfldr_spawn(-1, argv, data.data(), data.size());
	if (pid > 0) {
		log("update: installed %s (pid %d), relaunching", ver.c_str(), static_cast<int>(pid));
		notify(("GaelaniLIVE actualizado a " + (ver.empty() ? std::string("?") : ver) + ". Se relanza el payload...").c_str());
		_exit(0);
	}
	// No relaunch: the new elf stays installed for the next manual load.
	unlink(kAppliedFile);
	log("update: elfldr_spawn failed (%d); reload the payload by hand", static_cast<int>(pid));
	notify("GaelaniLIVE: elf nuevo instalado, pero no se pudo relanzar. Vuelve a cargar GaelaniLIVE a mano.");
}

std::string g_install_ver;

void* install_thread(void*) {
	sleep(2); // let the HTTP reply reach the page before the server goes away
	install_now(g_install_ver);
	return nullptr;
}

} // namespace

bool update_install_start(const std::string& ver, std::string& error) {
	if (!file_exists(kElfNew)) {
		error = "No hay ninguna actualización preparada";
		return false;
	}
	if (!elf_bytes_ok(kElfNew)) {
		unlink(kElfNew);
		error = "El archivo descargado no es un payload válido";
		return false;
	}
	g_install_ver = ver;
	pthread_t th;
	if (pthread_create(&th, nullptr, install_thread, nullptr) == 0) {
		pthread_detach(th);
	} else {
		error = "No se pudo preparar la instalación";
		return false;
	}
	return true;
}

} // namespace gaelanilive
