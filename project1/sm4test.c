#include <string.h>
#include <stdio.h>
#include "sm4.h"
#include <time.h>

int main(int argc, char** argv)
{
	unsigned char key[16] = {0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef, 0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10};
	unsigned char input[16] = {0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef, 0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10};
	unsigned char output[16];
	sm4_context ctx;
	unsigned long i;

	//encrypt standard testing vector
	sm4_setkey_enc(&ctx, key);
	sm4_crypt_ecb(&ctx, 1, 16, input, output);
	for (i = 0; i < 16; i++)
		printf("%02x ", output[i]);
	printf("\n");

	//decrypt testing
	sm4_setkey_dec(&ctx, key);
	sm4_crypt_ecb(&ctx, 0, 16, output, output);
	for (i = 0; i < 16; i++)
		printf("%02x ", output[i]);
	printf("\n");

	//decrypt 1M times testing vector based on standards.
	i = 0;
	sm4_setkey_enc(&ctx, key);
	clock_t start = clock();
	while (i < 100000)
	{
		sm4_crypt_ecb(&ctx, 1, 16, input, input);
		i++;
	}
	clock_t end = clock();
	double time_spent = (double)(end - start) / CLOCKS_PER_SEC;
	printf("Time spent for 1M encryptions: %f seconds\n", time_spent);
	for (i = 0; i < 16; i++)
		printf("%02x ", input[i]);
	printf("\n");

	return 0;
}
