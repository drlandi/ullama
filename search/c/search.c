/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   search.c                                         :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include <endian.h>
#include <string.h>
#include "msearch.h"

uint64_t	read_key(const uint8_t *rec)
{
	uint64_t	raw;

	memcpy(&raw, rec, sizeof(raw));
	return (be64toh(raw));
}

int64_t	search_mapped(const t_map *map, uint64_t key)
{
	int64_t		lo;
	int64_t		hi;
	int64_t		mid;
	uint64_t	cur;

	lo = 0;
	hi = (int64_t)map->count - 1;
	while (lo <= hi)
	{
		mid = lo + (hi - lo) / 2;
		cur = read_key(map->base + (size_t)mid * REC_SIZE);
		if (cur == key)
			return (mid);
		if (cur < key)
			lo = mid + 1;
		else
			hi = mid - 1;
	}
	return (-1);
}
