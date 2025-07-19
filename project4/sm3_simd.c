// Sample 1
// Input:"abc"
// Output:66c7f0f4 62eeedd9 d1f2d46b dc10e4e2 4167c487 5cf2f7a2 297da02b 8f4ba8e0

// Sample 2
// Input:"abcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd"
// Outpuf:debe9ff9 2275b8a1 38604889 c18e5a4d 6fdb70e5 387e5765 293dcba3 9c0c5732

#include "sm3.h"
#include <string.h>
#include <stdio.h>
#include <immintrin.h>

/*
 * 32-bit integer manipulation macros (big endian)
 */
#ifndef GET_ULONG_BE
#define GET_ULONG_BE(n,b,i)                             \
{                                                       \
    (n) = ( (uint32_t) (b)[(i)    ] << 24 )        \
        | ( (uint32_t) (b)[(i) + 1] << 16 )        \
        | ( (uint32_t) (b)[(i) + 2] <<  8 )        \
        | ( (uint32_t) (b)[(i) + 3]       );       \
}
#endif

#ifndef PUT_ULONG_BE
#define PUT_ULONG_BE(n,b,i)                             \
{                                                       \
    (b)[(i)    ] = (uint8_t) ( (n) >> 24 );       \
    (b)[(i) + 1] = (uint8_t) ( (n) >> 16 );       \
    (b)[(i) + 2] = (uint8_t) ( (n) >>  8 );       \
    (b)[(i) + 3] = (uint8_t) ( (n)       );       \
}
#endif

/*
 * SM3 context setup
 */
void sm3_starts( sm3_context *ctx )
{
    ctx->total[0] = 0;
    ctx->total[1] = 0;

    ctx->state[0] = 0x7380166F;
    ctx->state[1] = 0x4914B2B9;
    ctx->state[2] = 0x172442D7;
    ctx->state[3] = 0xDA8A0600;
    ctx->state[4] = 0xA96F30BC;
    ctx->state[5] = 0x163138AA;
    ctx->state[6] = 0xE38DEE4D;
    ctx->state[7] = 0xB0FB0E4E;

}

// 在sm3.c文件开头添加SIMD头文件
#include <immintrin.h>

// 添加SIMD辅助函数
static __m128i rotate_left_simd(__m128i a, int k)
{
    k = k % 32;
	__m128i tmp1, tmp2, tmp3;
	__m128i ze = _mm_set_epi32(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF);
	tmp1 = _mm_slli_epi32(a, k);
	tmp1 = _mm_and_si128(ze, tmp1);
	tmp2 = _mm_srli_epi32(_mm_and_si128(ze, a), 32-k);
	tmp3 = _mm_or_si128(tmp1, tmp2);
	return tmp3;
}

// 优化后的sm3_process函数
static void sm3_process_simd(sm3_context *ctx, uint8_t data[64])
{
    uint32_t SS1, SS2, TT1, TT2, W[68], W1[64];
    uint32_t A, B, C, D, E, F, G, H;
    uint32_t T[64];
    int j;

    // 初始化T数组
    for (j = 0; j < 16; j++)
        T[j] = 0x79CC4519;
    for (j = 16; j < 64; j++)
        T[j] = 0x7A879D8A;

    // 读取前16个字（保持原有方式）
    GET_ULONG_BE(W[0], data, 0);
    GET_ULONG_BE(W[1], data, 4);
    GET_ULONG_BE(W[2], data, 8);
    GET_ULONG_BE(W[3], data, 12);
    GET_ULONG_BE(W[4], data, 16);
    GET_ULONG_BE(W[5], data, 20);
    GET_ULONG_BE(W[6], data, 24);
    GET_ULONG_BE(W[7], data, 28);
    GET_ULONG_BE(W[8], data, 32);
    GET_ULONG_BE(W[9], data, 36);
    GET_ULONG_BE(W[10], data, 40);
    GET_ULONG_BE(W[11], data, 44);
    GET_ULONG_BE(W[12], data, 48);
    GET_ULONG_BE(W[13], data, 52);
    GET_ULONG_BE(W[14], data, 56);
    GET_ULONG_BE(W[15], data, 60);

#define FF0(x,y,z) ( (x) ^ (y) ^ (z))
#define FF1(x,y,z) (((x) & (y)) | ( (x) & (z)) | ( (y) & (z)))

#define GG0(x,y,z) ( (x) ^ (y) ^ (z))
#define GG1(x,y,z) (((x) & (y)) | ( (~(x)) & (z)) )


#define  SHL(x,n) (((x) & 0xFFFFFFFF) << n)
#define ROTL(x,n) (SHL((x),n) | ((x) >> (32 - n)))

#define P0(x) ((x) ^  ROTL((x),9) ^ ROTL((x),17))
#define P1(x) ((x) ^  ROTL((x),15) ^ ROTL((x),23))
    __m128i tmp1, tmp2, tmp3, tmp4, tmp5, tmp6, tmp7, tmp8, tmp9,tmp10;
    // 使用SIMD优化消息扩展 W[16] 到 W[67]
    for (j = 16; j < 68; j += 4) {
        int i=j+3;
		tmp9 = _mm_setr_epi32(W[j-16], W[j-15], W[j-14], W[j-13]);
		tmp4 = _mm_setr_epi32(W[j-13], W[j-12], W[j-11], W[j-10]);
		tmp5 = _mm_setr_epi32(W[j-9], W[j-8], W[j-7], W[j-6]);
		tmp6 = _mm_setr_epi32(W[j-3], W[j-2], W[j-1], 0);
		tmp7 = _mm_setr_epi32(W[j-6], W[j-5], W[j-4], W[j-3]);
		tmp1 = _mm_xor_si128(tmp9, tmp5);
		tmp2 = rotate_left_simd(tmp6, 15);
		tmp1 = _mm_xor_si128(tmp1, tmp2);
		tmp3 = _mm_xor_si128(tmp1, _mm_xor_si128(rotate_left_simd(tmp1, 15), rotate_left_simd(tmp1, 23)));
		tmp8 = _mm_xor_si128(rotate_left_simd(tmp4, 7), tmp7);
		tmp10 = _mm_xor_si128(tmp3, tmp8);
		//_mm_maskstore_epi32((int *)&W[j], _mm_set_epi32(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF), tmp10);
        _mm_storeu_si128((__m128i *)&W[j], tmp10);
		W[i] = P1(W[i - 16] ^ W[i - 9] ^ ROTL(W[i - 3], 15)) ^ ROTL(W[i - 13], 7) ^ W[i - 6];
    }

    /*for (int i = 0; i < 68; i++) { // 调试输出
        printf("0x%08X\t", W[i]);
        if ((i+1) % 8 == 0) printf("\n");
    }
    printf("\n");*/

    // 计算W1数组
    for (j = 0; j < 64; j += 4) {
        __m128i w_vec = _mm_loadu_si128((__m128i*)&W[j]);
        __m128i w_plus_4 = _mm_loadu_si128((__m128i*)&W[j + 4]);
        __m128i result = _mm_xor_si128(w_vec, w_plus_4);
        _mm_storeu_si128((__m128i*)&W1[j], result);
    }

    // 压缩函数主循环保持原有逻辑
    A = ctx->state[0];
    B = ctx->state[1];
    C = ctx->state[2];
    D = ctx->state[3];
    E = ctx->state[4];
    F = ctx->state[5];
    G = ctx->state[6];
    H = ctx->state[7];

    for (j = 0; j < 16; j++) {
        SS1 = ROTL((ROTL(A, 12) + E + ROTL(T[j], j)), 7);
        SS2 = SS1 ^ ROTL(A, 12);
        TT1 = FF0(A, B, C) + D + SS2 + W1[j];
        TT2 = GG0(E, F, G) + H + SS1 + W[j];
        D = C;
        C = ROTL(B, 9);
        B = A;
        A = TT1;
        H = G;
        G = ROTL(F, 19);
        F = E;
        E = P0(TT2);
    }

    for (j = 16; j < 64; j++) {
        SS1 = ROTL((ROTL(A, 12) + E + ROTL(T[j], j)), 7);
        SS2 = SS1 ^ ROTL(A, 12);
        TT1 = FF1(A, B, C) + D + SS2 + W1[j];
        TT2 = GG1(E, F, G) + H + SS1 + W[j];
        D = C;
        C = ROTL(B, 9);
        B = A;
        A = TT1;
        H = G;
        G = ROTL(F, 19);
        F = E;
        E = P0(TT2);
    }

    ctx->state[0] ^= A;
    ctx->state[1] ^= B;
    ctx->state[2] ^= C;
    ctx->state[3] ^= D;
    ctx->state[4] ^= E;
    ctx->state[5] ^= F;
    ctx->state[6] ^= G;
    ctx->state[7] ^= H;
}

/*
 * SM3 process buffer
 */
void sm3_update( sm3_context *ctx, uint8_t *input, int ilen ) //用于支持流式hash
{
    int fill;
    uint32_t left;

    if ( ilen <= 0 )
        return;

    left = ctx->total[0] & 0x3F; //计算当前缓冲区中剩余的字节数(总长度%64)
    fill = 64 - left; //需要填充的字节数

    ctx->total[0] += ilen;
    ctx->total[0] &= 0xFFFFFFFF;

    if ( ctx->total[0] < (uint32_t) ilen ) //进位
        ctx->total[1]++;

    if ( left && ilen >= fill )
    {
        memcpy( (void *) (ctx->buffer + left),
                (void *) input, fill );
        sm3_process_simd(ctx, ctx->buffer); //更新ctx->state
        input += fill;
        ilen  -= fill;
        left = 0;
    }

    while ( ilen >= 64 )
    {
        sm3_process_simd(ctx, input);
        input += 64;
        ilen  -= 64;
    }

    if ( ilen > 0 ) //如果不整除，则放在缓冲区中
    {
        memcpy( (void *) (ctx->buffer + left),
                (void *) input, ilen );
    }
}

static const uint8_t sm3_padding[64] =
{
    0x80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};

/*
 * SM3 final digest
 */
void sm3_finish( sm3_context *ctx, uint8_t output[32] )
{
    uint32_t last, padn;
    uint32_t high, low;
    uint8_t msglen[8];

    high = ( ctx->total[0] >> 29 )
           | ( ctx->total[1] <<  3 );
    low  = ( ctx->total[0] <<  3 );

    PUT_ULONG_BE( high, msglen, 0 );
    PUT_ULONG_BE( low,  msglen, 4 );

    last = ctx->total[0] & 0x3F; //计算剩余的字节数
    padn = ( last < 56 ) ? ( 56 - last ) : ( 120 - last );

    sm3_update( ctx, (uint8_t *) sm3_padding, padn ); //填充数据
    sm3_update( ctx, msglen, 8 );

    PUT_ULONG_BE( ctx->state[0], output,  0 ); //将最终的哈希值（存储在 ctx->state 中）复制到输出缓冲区
    PUT_ULONG_BE( ctx->state[1], output,  4 );
    PUT_ULONG_BE( ctx->state[2], output,  8 );
    PUT_ULONG_BE( ctx->state[3], output, 12 );
    PUT_ULONG_BE( ctx->state[4], output, 16 );
    PUT_ULONG_BE( ctx->state[5], output, 20 );
    PUT_ULONG_BE( ctx->state[6], output, 24 );
    PUT_ULONG_BE( ctx->state[7], output, 28 );
}

/*
 * output = SM3( input buffer )
 */
void sm3( uint8_t *input, int ilen,
          uint8_t output[32] )
{
    sm3_context ctx;

    sm3_starts( &ctx );
    sm3_update( &ctx, input, ilen ); //处理输入数据
    sm3_finish( &ctx, output ); //计算最终的哈希值（填充）

    memset( &ctx, 0, sizeof( sm3_context ) );
}

/*
 * output = SM3( file contents )
 */
int sm3_file( char *path, uint8_t output[32] )
{
    FILE *f;
    size_t n;
    sm3_context ctx;
    uint8_t buf[1024];

    if ( ( f = fopen( path, "rb" ) ) == NULL )
        return ( 1 );

    sm3_starts( &ctx );

    while ( ( n = fread( buf, 1, sizeof( buf ), f ) ) > 0 )
        sm3_update( &ctx, buf, (int) n );

    sm3_finish( &ctx, output );

    memset( &ctx, 0, sizeof( sm3_context ) );

    if ( ferror( f ) != 0 )
    {
        fclose( f );
        return ( 2 );
    }

    fclose( f );
    return ( 0 );
}

/*
 * SM3 HMAC context setup
 */
void sm3_hmac_starts( sm3_context *ctx, uint8_t *key, int keylen )
{
    int i;
    uint8_t sum[32];

    if ( keylen > 64 )
    {
        sm3( key, keylen, sum );
        keylen = 32;
        //keylen = ( is224 ) ? 28 : 32;
        key = sum;
    }

    memset( ctx->ipad, 0x36, 64 );
    memset( ctx->opad, 0x5C, 64 );

    for ( i = 0; i < keylen; i++ )
    {
        ctx->ipad[i] = (uint8_t)( ctx->ipad[i] ^ key[i] );
        ctx->opad[i] = (uint8_t)( ctx->opad[i] ^ key[i] );
    }

    sm3_starts( ctx);
    sm3_update( ctx, ctx->ipad, 64 );

    memset( sum, 0, sizeof( sum ) );
}

/*
 * SM3 HMAC process buffer
 */
void sm3_hmac_update( sm3_context *ctx, uint8_t *input, int ilen )
{
    sm3_update( ctx, input, ilen );
}

/*
 * SM3 HMAC final digest
 */
void sm3_hmac_finish( sm3_context *ctx, uint8_t output[32] )
{
    int hlen;
    uint8_t tmpbuf[32];

    //is224 = ctx->is224;
    hlen =  32;

    sm3_finish( ctx, tmpbuf );
    sm3_starts( ctx );
    sm3_update( ctx, ctx->opad, 64 );
    sm3_update( ctx, tmpbuf, hlen );
    sm3_finish( ctx, output );

    memset( tmpbuf, 0, sizeof( tmpbuf ) );
}

/*
 * output = HMAC-SM#( hmac key, input buffer )
 */
void sm3_hmac( uint8_t *key, int keylen,
               uint8_t *input, int ilen,
               uint8_t output[32] )
{
    sm3_context ctx;

    sm3_hmac_starts( &ctx, key, keylen);
    sm3_hmac_update( &ctx, input, ilen );
    sm3_hmac_finish( &ctx, output );

    memset( &ctx, 0, sizeof( sm3_context ) );
}








