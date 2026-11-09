#include "libmemctl.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sanitizer/asan_interface.h>

static void check_live(unsigned char *ptr, size_t size)
{
    const size_t accessible = size == 0U ? 1U : size;
    assert(ptr != NULL);
    assert(__asan_region_is_poisoned(ptr, accessible) == NULL);
    assert(__asan_address_is_poisoned(ptr - 1));
    assert(__asan_address_is_poisoned(ptr + accessible));
    memset(ptr, 0xa5, accessible);
}

int main(void)
{
    static const size_t boundaries[] = {
        255, 256, 257, 319, 320, 321, 1023, 1024, 1025,
        1279, 1280, 1281, 4095, 4096, 4097, 5119, 5120, 5121,
        16383, 16384, 16385, 20479, 20480, 20481,
        65535, 65536, 65537, 69616, 69617, 131072, 1048576
    };
    unsigned char *ptr;
    unsigned char *resized;
    size_t index;
    for (index = 0; index <= 129U; ++index) {
        ptr = my_malloc(index);
        check_live(ptr, index);
        my_free(ptr);
    }
    for (index = 0; index < sizeof(boundaries) / sizeof(boundaries[0]); ++index) {
        ptr = my_malloc(boundaries[index]);
        check_live(ptr, boundaries[index]);
        my_free(ptr);
    }
    ptr = my_calloc(3, 11);
    assert(ptr != NULL);
    for (index = 0; index < 33; ++index) assert(ptr[index] == 0);
    check_live(ptr, 33);
    resized = my_realloc(ptr, 47);
    assert(resized == ptr);
    check_live(resized, 47);
    resized = my_realloc(ptr, 33);
    assert(resized == ptr);
    check_live(resized, 33);
    assert(my_realloc(ptr, SIZE_MAX) == NULL);
    assert(ptr[32] == 0xa5);
    check_live(ptr, 33);
    resized = my_realloc(ptr, 65537);
    assert(resized != NULL && resized != ptr);
    for (index = 0; index < 33; ++index) assert(resized[index] == 0xa5);
    check_live(resized, 65537);
    ptr = resized;
    resized = my_realloc(ptr, 68000);
    assert(resized == ptr);
    check_live(resized, 68000);
    resized = my_realloc(ptr, 67600);
    assert(resized == ptr);
    check_live(resized, 67600);
    resized = my_realloc(ptr, 64);
    assert(resized != NULL && resized != ptr);
    for (index = 0; index < 64; ++index) assert(resized[index] == 0xa5);
    check_live(resized, 64);
    my_free(resized);
    memctl_trim();
    ptr = my_malloc(33);
    check_live(ptr, 33);
    my_free(ptr);
    /* This fresh, small empty region is cached: its payload remains mapped. */
    assert(__asan_address_is_poisoned(ptr));
    assert(__asan_address_is_poisoned(ptr + 32));
    resized = my_malloc(33);
    assert(resized == ptr);
    check_live(resized, 33);
    my_free(resized);
    memctl_trim();
    /* Exercise shadow clearing when mappings are returned and later reused. */
    for (index = 0; index < 100; ++index) {
        ptr = my_malloc(65537);
        check_live(ptr, 65537);
        my_free(ptr);
    }
    memctl_trim();
    puts("PASS: exact payload, protected headers/tails, realloc, cache/reuse shadow");
    return 0;
}
