/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   bench.c                                          :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "msearch.h"

static int	run_pass(t_bench *b)
{
	size_t		i;
	uint64_t	t0;
	int64_t		got;

	i = 0;
	while (i < b->count)
	{
		t0 = now_ns();
		if (b->percall)
			got = search_file(b->path, b->queries[i].key);
		else
			got = search_mapped(b->map, b->queries[i].key);
		b->times[i] = now_ns() - t0;
		if (got != b->queries[i].expected)
		{
			printf("MISMATCH: key %lu returned %ld, expected %ld\n",
				b->queries[i].key, got, b->queries[i].expected);
			return (1);
		}
		i++;
	}
	return (0);
}

static int	report_pass(t_bench *b, const char *label)
{
	long	min0;
	long	maj0;
	long	min1;
	long	maj1;

	read_faults(&min0, &maj0);
	if (run_pass(b))
		return (1);
	read_faults(&min1, &maj1);
	print_stats(label, b->times, b->count);
	printf("  %-18s  page faults per query: minor %.2f, major %.3f\n", "",
		(min1 - min0) / (double)b->count, (maj1 - maj0) / (double)b->count);
	return (0);
}

static int	run_all(t_bench *b, const char *mode)
{
	char	label[32];

	snprintf(label, sizeof(label), "C %s first", mode);
	if (report_pass(b, label))
		return (1);
	snprintf(label, sizeof(label), "C %s warm", mode);
	return (report_pass(b, label));
}

static int	setup(t_bench *b, t_map *map, char **argv)
{
	memset(b, 0, sizeof(*b));
	b->path = argv[1];
	b->percall = (strcmp(argv[3], "percall") == 0);
	b->queries = load_queries(argv[2], &b->count);
	if (!b->queries || !b->count)
		return (1);
	b->times = malloc(b->count * sizeof(uint64_t));
	drop_cache(argv[1]);
	if (!b->percall && map_open(map, argv[1]))
		return (1);
	b->map = map;
	return (!b->times);
}

int	main(int argc, char **argv)
{
	t_bench	b;
	t_map	map;
	int		ret;

	if (argc != 4 || (strcmp(argv[3], "percall") && strcmp(argv[3], "mapped")))
	{
		fprintf(stderr, "usage: %s DATAFILE QUERIES percall|mapped\n", argv[0]);
		return (2);
	}
	memset(&map, 0, sizeof(map));
	ret = setup(&b, &map, argv);
	if (!ret)
		printf("file: %s   queries: %zu   mode: %s   (cache dropped first)\n",
			argv[1], b.count, argv[3]);
	if (!ret)
		ret = run_all(&b, argv[3]);
	map_close(&map);
	free((void *)b.queries);
	free(b.times);
	return (ret);
}
