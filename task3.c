/*
Jiaqi Liu — 34422242
Shengyuan Jin — 344172573
*/
#define _POSIX_C_SOURCE 199309L

#include <errno.h>
#include <limits.h>
#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define OUTPUT_THRESHOLD 100
#define OUTPUT_FILE "primes3.txt"

static int IsPrime(int number);
static int ParseInteger(const char *text, int minimum, int *value);
static int WriteToFile(const char *pFilename,
                       const unsigned char *pResult,
                       int n);
static double ElapsedSeconds(struct timespec start, struct timespec end);

int main(int argc, char *argv[])
{
    int n;
    int numThreads;
    int benchmarkMode = 0;
    int actualThreads = 0;
    int candidate;
    int primeCount = 0;
    unsigned char *pIsPrime;
    struct timespec start;
    struct timespec end;
    struct timespec startComp;
    struct timespec endComp;
    double computationTime;

    if (argc == 4 && strcmp(argv[3], "--benchmark") == 0)
    {
        benchmarkMode = 1;
    }
    else if (argc != 1 && argc != 3)
    {
        fprintf(stderr, "Usage: %s [n threads [--benchmark]]\n", argv[0]);
        return EXIT_FAILURE;
    }

    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0)
    {
        perror("clock_gettime");
        return EXIT_FAILURE;
    }

    if (argc >= 3)
    {
        if (!ParseInteger(argv[1], 0, &n) ||
            !ParseInteger(argv[2], 1, &numThreads))
        {
            fprintf(stderr, "Error: n must be non-negative and threads must be positive.\n");
            return EXIT_FAILURE;
        }
    }
    else
    {
        printf("Prime Number Finder - OpenMP!\n\n");

        printf("Enter n: ");
        if (scanf("%d", &n) != 1 || n < 0)
        {
            fprintf(stderr, "Invalid input.\n");
            return EXIT_FAILURE;
        }

        printf("Enter number of threads: ");
        if (scanf("%d", &numThreads) != 1 || numThreads <= 0)
        {
            fprintf(stderr, "Invalid number of threads.\n");
            return EXIT_FAILURE;
        }
    }

    pIsPrime = calloc((size_t)(n > 0 ? n : 1), sizeof(*pIsPrime));
    if (pIsPrime == NULL)
    {
        fprintf(stderr, "Memory allocation failed.\n");
        return EXIT_FAILURE;
    }

    if (n > 2)
    {
        pIsPrime[2] = 1;
    }

    /* Disable adjustment so the requested thread count is used. */
    omp_set_dynamic(0);

    if (!benchmarkMode)
    {
        printf("Compute\n");
    }

    if (clock_gettime(CLOCK_MONOTONIC, &startComp) != 0)
    {
        perror("clock_gettime");
        free(pIsPrime);
        return EXIT_FAILURE;
    }

    /*
     * Each loop iteration checks one odd candidate. With a chunk size of 1,
     * static scheduling distributes the candidates cyclically:
     * thread 0 gets 3, 3 + 2T, ...; thread 1 gets 5, 5 + 2T, ...
     * This matches the cyclic partitioning used by the POSIX Threads version.
     */
#pragma omp parallel default(none) \
    shared(n, numThreads, pIsPrime, actualThreads) num_threads(numThreads)
    {
#pragma omp master
        actualThreads = omp_get_num_threads();

#pragma omp for schedule(static, 1)
        for (candidate = 3; candidate < n; candidate += 2)
        {
            if (IsPrime(candidate))
            {
                pIsPrime[candidate] = 1;
            }
        }
    }

    if (clock_gettime(CLOCK_MONOTONIC, &endComp) != 0)
    {
        perror("clock_gettime");
        free(pIsPrime);
        return EXIT_FAILURE;
    }

    computationTime = ElapsedSeconds(startComp, endComp);

    for (candidate = 2; candidate < n; ++candidate)
    {
        if (pIsPrime[candidate])
        {
            ++primeCount;
        }
    }

    if (benchmarkMode)
    {
        printf("RESULT,openmp,%d,%d,%.9f,%d\n",
               n, actualThreads, computationTime, primeCount);
        free(pIsPrime);
        return EXIT_SUCCESS;
    }

    printf("Prime search complete - Computational time only(s): %.6f\n",
           computationTime);
    printf("OpenMP threads used: %d\n", actualThreads);

    if (n < OUTPUT_THRESHOLD)
    {
        int first = 1;

        printf("Prime numbers less than %d:\n", n);
        for (candidate = 2; candidate < n; ++candidate)
        {
            if (pIsPrime[candidate])
            {
                printf("%s%d", first ? "" : ", ", candidate);
                first = 0;
            }
        }
        putchar('\n');
    }
    else
    {
        printf("Commence Writing\n");
        if (!WriteToFile(OUTPUT_FILE, pIsPrime, n))
        {
            free(pIsPrime);
            return EXIT_FAILURE;
        }
        printf("Write complete\n");
        printf("Prime numbers saved to %s\n", OUTPUT_FILE);
    }

    printf("Number of primes found: %d\n", primeCount);

    free(pIsPrime);

    if (clock_gettime(CLOCK_MONOTONIC, &end) != 0)
    {
        perror("clock_gettime");
        return EXIT_FAILURE;
    }

    printf("Overall time(s): %.6f\n", ElapsedSeconds(start, end));
    return EXIT_SUCCESS;
}

static int IsPrime(int number)
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

    limit = (int)sqrt((double)number);
    for (divisor = 3; divisor <= limit; divisor += 2)
    {
        if (number % divisor == 0)
        {
            return 0;
        }
    }

    return 1;
}

static int ParseInteger(const char *text, int minimum, int *value)
{
    char *end = NULL;
    long parsed;

    errno = 0;
    parsed = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' ||
        parsed < minimum || parsed > INT_MAX)
    {
        return 0;
    }

    *value = (int)parsed;
    return 1;
}

static int WriteToFile(const char *pFilename,
                       const unsigned char *pResult,
                       int n)
{
    int candidate;
    int first = 1;
    FILE *pFile = fopen(pFilename, "w");

    if (pFile == NULL)
    {
        perror("Error opening output file");
        return 0;
    }

    for (candidate = 2; candidate < n; ++candidate)
    {
        if (pResult[candidate])
        {
            fprintf(pFile, "%s%d", first ? "" : ", ", candidate);
            first = 0;
        }
    }
    fputc('\n', pFile);

    if (fclose(pFile) != 0)
    {
        perror("Error closing output file");
        return 0;
    }

    return 1;
}

static double ElapsedSeconds(struct timespec start, struct timespec end)
{
    return (double)(end.tv_sec - start.tv_sec) +
           (double)(end.tv_nsec - start.tv_nsec) / 1000000000.0;
}
