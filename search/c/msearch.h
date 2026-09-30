/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   msearch.h                                        :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#ifndef MSEARCH_H
# define MSEARCH_H

# include <stddef.h>
# include <stdint.h>

# define REC_SIZE 24

typedef struct s_query
{
	uint64_t	key;
	int64_t		expected;
}	t_query;

typedef struct s_map
{
	const uint8_t	*base;
	size_t			count;
	size_t			len;
}	t_map;

typedef struct s_bench
{
	const char		*path;
	const t_map		*map;
	const t_query	*queries;
	size_t			count;
	uint64_t		*times;
	int				percall;
}	t_bench;

uint64_t	read_key(const uint8_t *rec);
int64_t		search_mapped(const t_map *map, uint64_t key);
int			map_open(t_map *map, const char *path);
void		map_close(t_map *map);
int64_t		search_file(const char *path, uint64_t key);
t_query		*load_queries(const char *path, size_t *count);
void		print_stats(const char *label, uint64_t *times, size_t n);
uint64_t	now_ns(void);
void		drop_cache(const char *path);
void		read_faults(long *minor, long *major);

#endif
