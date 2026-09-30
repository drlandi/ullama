/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   stats.c                                          :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "msearch.h"

uint64_t	now_ns(void)
{
	struct timespec	ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ((uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec);
}

static int	cmp_u64(const void *a, const void *b)
{
	uint64_t	x;
	uint64_t	y;

	x = *(const uint64_t *)a;
	y = *(const uint64_t *)b;
	if (x < y)
		return (-1);
	return (x > y);
}

static double	median_us(const uint64_t *sorted, size_t n)
{
	if (n % 2)
		return (sorted[n / 2] / 1000.0);
	return ((sorted[n / 2 - 1] + sorted[n / 2]) / 2000.0);
}

static double	pct_us(const uint64_t *sorted, size_t n, double q)
{
	size_t	i;

	i = (size_t)(q * n);
	if (i > n - 1)
		i = n - 1;
	return (sorted[i] / 1000.0);
}

void	print_stats(const char *label, uint64_t *times, size_t n)
{
	qsort(times, n, sizeof(uint64_t), cmp_u64);
	printf("  %-18s: median %8.1f us   p95 %8.1f us   p99 %8.1f us"
		"   max %10.1f us\n", label, median_us(times, n),
		pct_us(times, n, 0.95), pct_us(times, n, 0.99),
		times[n - 1] / 1000.0);
}
