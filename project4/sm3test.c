#include <string.h>
#include <stdio.h>
#include "sm3.h"
#include <time.h>

int main()
{
	uint8_t *input = (uint8_t *)"abc";
	int ilen = 3;
	uint8_t output[32];
	int i;
	sm3_context ctx;

	printf("Message:\n");
	printf("%s\n", input);

	sm3(input, ilen, output);
	printf("Hash:\n   ");
	for (i = 0; i < 32; i++)
	{
		printf("%02x", output[i]);
		if (((i + 1) % 4 ) == 0) printf(" ");
	}
	printf("\n");

	printf("Message:\n");
	for (i = 0; i < 16; i++)
		printf("abcd");
	printf("\n");

	sm3_starts( &ctx );
	for (i = 0; i < 16; i++) //流式hash
		sm3_update( &ctx, (uint8_t *)"abcd", 4 );
	sm3_finish( &ctx, output );
	memset( &ctx, 0, sizeof( sm3_context ) );

	printf("Hash:\n   ");
	for (i = 0; i < 32; i++)
	{
		printf("%02x", output[i]);
		if (((i + 1) % 4 ) == 0) printf(" ");
	}
	printf("\n");
	//getch();	//VS2008
	printf("Message:abcd*1M\n"); //测试时间

	clock_t start = clock();
	sm3_starts( &ctx );
	for (i = 0; i < 1000000; i++) //流式hash
		sm3_update( &ctx, (uint8_t *)"abcd", 4 );
	sm3_finish( &ctx, output );
	memset( &ctx, 0, sizeof( sm3_context ) );
	clock_t end = clock();
	double time_spent = (double)(end - start) / CLOCKS_PER_SEC;
	printf("Time spent for 1M encryptions: %f seconds\n", time_spent);

	printf("Hash:\n   ");
	for (i = 0; i < 32; i++)
	{
		printf("%02x", output[i]);
		if (((i + 1) % 4 ) == 0) printf(" ");
	}
	printf("\n");
}