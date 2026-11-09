#include "libmemctl.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    size_t size;
    volatile unsigned char *ptr;
    assert(argc == 3);
    size = (size_t)strtoul(argv[2], NULL, 10);
    ptr = my_malloc(size);
    assert(ptr != NULL);
    if (strcmp(argv[1], "valid") == 0) {
        ptr[size == 0U ? 0U : size - 1U] = 42;
        my_free((void *)ptr);
        memctl_trim();
        puts("PASS: valid control");
        return 0;
    }
    if (strcmp(argv[1], "underflow") == 0) {
        ptr[-1] = 42;
    } else if (strcmp(argv[1], "freed") == 0) {
        my_free((void *)ptr);
        ptr[0] = 42;
    } else if (strcmp(argv[1], "reused") == 0) {
        void *resized;
        my_free((void *)ptr);
        resized = my_calloc(1, size);
        assert(resized == (void *)ptr);
        ptr[size] = 42;
    } else if (strcmp(argv[1], "shrink") == 0) {
        void *resized = my_realloc((void *)ptr, 33);
        assert(resized == (void *)ptr);
        ptr[33] = 42;
    } else if (strcmp(argv[1], "grow") == 0) {
        void *resized = my_realloc((void *)ptr, 47);
        assert(resized == (void *)ptr);
        ptr[46] = 42;
        ptr[47] = 42;
    } else {
        assert(strcmp(argv[1], "overrun") == 0);
        ptr[size == 0U ? 1U : size] = 42;
    }
    fputs("FAIL: invalid access escaped detection\n", stderr);
    return 0;
}
