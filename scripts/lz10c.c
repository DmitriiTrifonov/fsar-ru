// Fast Nintendo LZ10 compressor (greedy, hash chains). Build: see scripts/build_native.sh
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define WINDOW 4096
#define MAXLEN 18
#define HBITS 15
#define MAXCHAIN 256

// out must have room for len + len/8 + 8 bytes. Returns compressed size, or -1.
long lz10_compress(const uint8_t *in, long n, uint8_t *out) {
    if (n < 0 || n > 0xFFFFFF) return -1;
    int32_t *head = malloc(sizeof(int32_t) << HBITS);
    int32_t *prev = malloc(sizeof(int32_t) * (n > 0 ? n : 1));
    if (!head || !prev) { free(head); free(prev); return -1; }
    memset(head, 0xFF, sizeof(int32_t) << HBITS);
    out[0] = 0x10; out[1] = n & 255; out[2] = (n >> 8) & 255; out[3] = (n >> 16) & 255;
    long op = 4, pos = 0, inserted = 0;
    while (pos < n) {
        long flag_pos = op++; uint8_t flags = 0;
        for (int bit = 0; bit < 8 && pos < n; bit++) {
            long best_len = 0, best_disp = 0;
            if (pos + 3 <= n) {
                // make sure every position before pos is in the hash table
                for (; inserted < pos; inserted++) {
                    if (inserted + 3 > n) break;
                    uint32_t h = ((in[inserted] << 10) ^ (in[inserted+1] << 5) ^ in[inserted+2]) & ((1 << HBITS) - 1);
                    prev[inserted] = head[h]; head[h] = (int32_t)inserted;
                }
                uint32_t h = ((in[pos] << 10) ^ (in[pos+1] << 5) ^ in[pos+2]) & ((1 << HBITS) - 1);
                int32_t cand = head[h]; int chain = 0;
                long maxl = n - pos < MAXLEN ? n - pos : MAXLEN;
                while (cand >= 0 && pos - cand <= WINDOW && chain++ < MAXCHAIN) {
                    long l = 0;
                    while (l < maxl && in[cand + l] == in[pos + l]) l++;
                    if (l > best_len) { best_len = l; best_disp = pos - cand; if (l == maxl) break; }
                    cand = prev[cand];
                }
            }
            if (best_len >= 3) {
                flags |= 0x80 >> bit;
                long d = best_disp - 1;
                out[op++] = (uint8_t)(((best_len - 3) << 4) | (d >> 8));
                out[op++] = (uint8_t)(d & 255);
                pos += best_len;
            } else {
                out[op++] = in[pos++];
            }
        }
        out[flag_pos] = flags;
    }
    free(head); free(prev);
    return op;
}

// Optimal-parse LZ10 (same format, usually 2-6% smaller than the greedy one). out must have room for len + len/8 + 8 bytes.
long lz10_compress_opt(const uint8_t *in, long n, uint8_t *out) {
    if (n < 0 || n > 0xFFFFFF) return -1;
    int32_t *cost = malloc(sizeof(int32_t) * (n + 1));
    int16_t *tl = malloc(sizeof(int16_t) * (n + 1));      // token length ending at i (1 = literal)
    int16_t *td = malloc(sizeof(int16_t) * (n + 1));      // displacement of that token
    if (!cost || !tl || !td) { free(cost); free(tl); free(td); return -1; }
    for (long i = 0; i <= n; i++) cost[i] = 0x3FFFFFFF;
    cost[0] = 0;
    for (long i = 0; i < n; i++) {
        if (cost[i] + 9 < cost[i + 1]) { cost[i + 1] = cost[i] + 9; tl[i + 1] = 1; td[i + 1] = 0; }
        long maxl = n - i < MAXLEN ? n - i : MAXLEN, best_len = 0, best_disp = 0;
        long lim = i < WINDOW ? i : WINDOW;
        for (long d = 1; d <= lim; d++) {
            long l = 0;
            while (l < maxl && in[i - d + l] == in[i + l]) l++;
            if (l > best_len) { best_len = l; best_disp = d; if (l == maxl) break; }
        }
        for (long l = 3; l <= best_len; l++)
            if (cost[i] + 17 < cost[i + l]) { cost[i + l] = cost[i] + 17; tl[i + l] = (int16_t)l; td[i + l] = (int16_t)best_disp; }
    }
    // backtrack into a token list
    long ntok = 0; for (long i = n; i > 0; i -= tl[i]) ntok++;
    int32_t *tokpos = malloc(sizeof(int32_t) * (ntok + 1));
    long k = ntok; for (long i = n; i > 0; i -= tl[i]) tokpos[--k] = (int32_t)i;   // end position of token k
    out[0] = 0x10; out[1] = n & 255; out[2] = (n >> 8) & 255; out[3] = (n >> 16) & 255;
    long op = 4, flag_pos = 0; int bit = 8; uint8_t flags = 0;
    for (long t = 0; t < ntok; t++) {
        if (bit == 8) { if (t) out[flag_pos] = flags; flag_pos = op++; flags = 0; bit = 0; }
        long end = tokpos[t], l = tl[end], start = end - l;
        if (l >= 3) {
            flags |= 0x80 >> bit; long d = td[end] - 1;
            out[op++] = (uint8_t)(((l - 3) << 4) | (d >> 8)); out[op++] = (uint8_t)(d & 255);
        } else out[op++] = in[start];
        bit++;
    }
    out[flag_pos] = flags;
    free(cost); free(tl); free(td); free(tokpos);
    return op;
}
