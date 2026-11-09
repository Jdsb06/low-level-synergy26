#include "libmemctl.h"

#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    const size_t initial_count = 8;
    const size_t expanded_count = 32;
    int *values = my_calloc(initial_count, sizeof(*values));

    if (values == NULL) {
        perror("my_calloc");
        return EXIT_FAILURE;
    }
    for (size_t i = 0; i < initial_count; ++i) {
        if (values[i] != 0) {
            (void)fprintf(stderr, "calloc did not zero the requested storage\n");
            my_free(values);
            return EXIT_FAILURE;
        }
        values[i] = (int)i + 1;
    }
    (void)puts("calloc: 8 zeroed items");

    int *expanded = my_realloc(values, expanded_count * sizeof(*values));
    if (expanded == NULL) {
        perror("my_realloc");
        my_free(values);
        return EXIT_FAILURE;
    }
    values = expanded;
    for (size_t i = 0; i < initial_count; ++i) {
        if (values[i] != (int)i + 1) {
            (void)fprintf(stderr, "realloc did not preserve the original values\n");
            my_free(values);
            return EXIT_FAILURE;
        }
    }
    (void)puts("realloc: 8 values preserved in a 32-item buffer");
    my_free(values);
    memctl_trim();
    (void)puts("free + trim: example complete");
    return EXIT_SUCCESS;
}
