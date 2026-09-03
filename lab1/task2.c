/*
Jiaqi Liu — 34422242
Shengyuan Jin — 34417257
*/

#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <pthread.h>

int n;
int numThreads;
unsigned char *pIsPrime = NULL;

int IsPrime(int number);
void *ThreadFunc(void *pArg);
void WriteToFile(char *pFilename, unsigned char *pResult, int n);

int main()
{
    int i;
    int primeCount = 0;

    pthread_t *tid = NULL;
    int *threadNum = NULL;

    struct timespec start, end, startComp, endComp;
    double time_taken;

    // Overall timer starts
    clock_gettime(CLOCK_MONOTONIC, &start);

    printf("Prime Number Finder - POSIX Threads!\n\n");

    // Get n
    printf("Enter n: ");

    if (scanf("%d", &n) != 1 || n < 0)
    {
        printf("Invalid input.\n");
        return 0;
    }

    // Get number of threads
    printf("Enter number of threads: ");

    if (scanf("%d", &numThreads) != 1 || numThreads <= 0)
    {
        printf("Invalid number of threads.\n");
        return 0;
    }

    // Allocate shared result array.
    // calloc sets every element to 0 initially.
    pIsPrime = (unsigned char *)calloc(n, sizeof(unsigned char));

    if (pIsPrime == NULL && n > 0)
    {
        printf("Memory allocation failed.\n");
        return 0;
    }

    // Allocate thread IDs
    tid = (pthread_t *)malloc(numThreads * sizeof(pthread_t));
    threadNum = (int *)malloc(numThreads * sizeof(int));

    if (tid == NULL || threadNum == NULL)
    {
        printf("Memory allocation failed.\n");

        free(pIsPrime);
        free(tid);
        free(threadNum);

        return 0;
    }

    if (n > 2)
    {
        pIsPrime[2] = 1;
    }

    printf("Compute\n");

    // Computational timer starts
    clock_gettime(CLOCK_MONOTONIC, &startComp);

    for (i = 0; i < numThreads; i++)
    {
        threadNum[i] = i;

        if (pthread_create(&tid[i], NULL,
                           ThreadFunc, &threadNum[i]) != 0)
        {
            printf("Error creating thread %d\n", i);
            exit(EXIT_FAILURE);
        }
    }

    // Join - Wait until all worker threads finish
    for (i = 0; i < numThreads; i++)
    {
        pthread_join(tid[i], NULL);
    }

    // Computational timer ends
    clock_gettime(CLOCK_MONOTONIC, &endComp);

    time_taken =
        (endComp.tv_sec - startComp.tv_sec) * 1e9;

    time_taken +=
        (endComp.tv_nsec - startComp.tv_nsec);

    time_taken *= 1e-9;

    printf("Prime search complete - Computational time only(s): %lf\n",
           time_taken);

    // Count primes
    for (i = 2; i < n; i++)
    {
        if (pIsPrime[i])
        {
            primeCount++;
        }
    }

    // Output
    if (n < 100)
    {
        int first = 1;

        printf("Prime numbers less than %d:\n", n);

        for (i = 2; i < n; i++)
        {
            if (pIsPrime[i])
            {
                if (!first)
                {
                    printf(", ");
                }

                printf("%d", i);
                first = 0;
            }
        }

        printf("\n");
    }
    else
    {
        printf("Commence Writing\n");

        WriteToFile("primes2.txt", pIsPrime, n);

        printf("Write complete\n");
        printf("Prime numbers saved to primes.txt\n");
    }

    printf("Number of primes found: %d\n", primeCount);

    // Free memory
    free(tid);
    free(threadNum);
    free(pIsPrime);

    // Overall timer ends
    clock_gettime(CLOCK_MONOTONIC, &end);

    time_taken =
        (end.tv_sec - start.tv_sec) * 1e9;

    time_taken +=
        (end.tv_nsec - start.tv_nsec);

    time_taken *= 1e-9;

    printf("Overall time(s): %lf\n", time_taken);

    return 0;
}


// Thread function
void *ThreadFunc(void *pArg)
{
    int my_rank = *((int *)pArg);

    int candidate = 3 + (my_rank * 2);

    int step = numThreads * 2;

    for (; candidate < n; candidate += step)
    {
        if (IsPrime(candidate))
        {
            pIsPrime[candidate] = 1;
        }
    }

    return NULL;
}


int IsPrime(int number)
{
    int divisor;
    int limit;

    if (number < 2)
    {
        return 0;
    }

    if (number == 2)
    {
        return 1;
    }

    if (number % 2 == 0)
    {
        return 0;
    }

    limit = (int)sqrt(number);

    for (divisor = 3; divisor <= limit; divisor += 2)
    {
        if (number % divisor == 0)
        {
            return 0;
        }
    }

    return 1;
}


void WriteToFile(char *pFilename,
                 unsigned char *pResult,
                 int n)
{
    int i;
    int first = 1;

    FILE *pFile = fopen(pFilename, "w");

    if (pFile == NULL)
    {
        printf("Error: Cannot open file\n");
        return;
    }

    for (i = 2; i < n; i++)
    {
        if (pResult[i])
        {
            if (!first)
            {
                fprintf(pFile, ", ");
            }

            fprintf(pFile, "%d", i);

            first = 0;
        }
    }

    fprintf(pFile, "\n");

    fclose(pFile);
}