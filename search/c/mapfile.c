/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   mapfile.c                                        :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include <fcntl.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include "msearch.h"

static void	map_fd(t_map *map, int fd)
{
	struct stat	st;
	void		*addr;

	if (fstat(fd, &st) != 0 || st.st_size <= 0)
		return ;
	addr = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
	if (addr == MAP_FAILED)
		return ;
	if (getenv("MSEARCH_RANDOM"))
		madvise(addr, st.st_size, MADV_RANDOM);
	map->base = addr;
	map->len = st.st_size;
	map->count = st.st_size / REC_SIZE;
}

int	map_open(t_map *map, const char *path)
{
	int	fd;

	map->base = NULL;
	map->count = 0;
	map->len = 0;
	fd = open(path, O_RDONLY);
	if (fd < 0)
		return (1);
	map_fd(map, fd);
	close(fd);
	return (0);
}

void	map_close(t_map *map)
{
	if (map->base)
		munmap((void *)map->base, map->len);
	map->base = NULL;
}

int64_t	search_file(const char *path, uint64_t key)
{
	t_map	map;
	int64_t	found;

	if (map_open(&map, path))
		return (-2);
	found = search_mapped(&map, key);
	map_close(&map);
	return (found);
}
