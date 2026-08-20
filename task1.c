/*
Jiaqi Liu — 34422242
Shengyuan Jin — 344172573
*/

#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>


// Function prototypes
int IsPrime(int number);
void WriteToFile(char *pFilename, int *pPrimes, int count);

int main()
{
    int n;
    int i;
    int count = 0;
    int *pPrimes = NULL;

    struct timespec start, end, startComp, endComp;
    double time_taken;

    // Overall timer starts
    clock_gettime(CLOCK_MONOTONIC, &start);

    printf("Prime Number Finder!\n\n");

    printf("Enter n: ");
    if (scanf("%d", &n) != 1)
    {
        printf("Invalid input.\n");
        return 0;
    }

    if (n <= 2)
    {
        printf("There are no prime numbers less than %d.\n", n);
        return 0;
    }

    /*
     * Allocate enough memory for the worst case.
     * Not every number will be prime, but n integers is
     * more than enough storage.
     */
    pPrimes = (int *)malloc(n * sizeof(int));

    if (pPrimes == NULL)
    {
        printf("Memory allocation failed.\n");
        return 0;
    }

    printf("Compute\n");

    // Computational timer starts
    clock_gettime(CLOCK_MONOTONIC, &startComp);

    // Check odd number from 3
    pPrimes[count++] = 2;

    for (i = 3; i < n; i += 2)
    {
        if (IsPrime(i))
        {
            pPrimes[count] = i;
            count++;
        }
    }

    // Computational timer ends
    clock_gettime(CLOCK_MONOTONIC, &endComp);

    time_taken = (endComp.tv_sec - startComp.tv_sec) * 1e9;
    time_taken += (endComp.tv_nsec - startComp.tv_nsec);
    time_taken *= 1e-9;

    printf("Prime search complete - Computational time only(s): %lf\n",
           time_taken);

    /*
     * Small n: print to standard output
     * Large n: write to file
     */
    if (n < 100)
    {
        printf("Prime numbers less than %d:\n", n);

        for (i = 0; i < count; i++)
        {
            printf("%d", pPrimes[i]);

            if (i < count - 1)
            {
                printf(", ");
            }
        }

        printf("\n");
    }
    else
    {
        printf("Commence Writing\n");

        WriteToFile("primes.txt", pPrimes, count);

        printf("Write complete\n");
        printf("Prime numbers saved to primes.txt\n");
    }

    printf("Number of primes found: %d\n", count);

    free(pPrimes);

    // Overall timer ends
    clock_gettime(CLOCK_MONOTONIC, &end);

    time_taken = (end.tv_sec - start.tv_sec) * 1e9;
    time_taken += (end.tv_nsec - start.tv_nsec);
    time_taken *= 1e-9;

    printf("Overall time(s): %lf\n", time_taken);

    return 0;
}

// Check whether a number is prime
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

    // Only check odd divisors up to sqrt(number)
    for (divisor = 3; divisor <= limit; divisor += 2)
    {
        if (number % divisor == 0)
        {
            return 0;
        }
    }

    return 1;
}

// Write prime numbers to a text file
void WriteToFile(char *pFilename, int *pPrimes, int count)
{
    int i;

    FILE *pFile = fopen(pFilename, "w");

    if (pFile == NULL)
    {
        printf("Error: Cannot open file\n");
        return;
    }

    for (i = 0; i < count; i++)
    {
        fprintf(pFile, "%d", pPrimes[i]);

        if (i < count - 1)
        {
            fprintf(pFile, ", ");
        }
    }

    fprintf(pFile, "\n");

    fclose(pFile);
}