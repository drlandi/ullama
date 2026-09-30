/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   queries.c                                        :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include <stdlib.h>
#include "msearch.h"

static long	file_size(FILE *f)
{
	fseek(f, 0, SEEK_END);
	return (ftell(f));
}

t_query	*load_queries(const char *path, size_t *count)
{
	FILE	*f;
	long	size;
	t_query	*q;

	*count = 0;
	f = fopen(path, "rb");
	if (!f)
		return (NULL);
	size = file_size(f);
	rewind(f);
	q = malloc(size);
	if (q && fread(q, sizeof(t_query), size / sizeof(t_query), f)
		== size / sizeof(t_query))
		*count = size / sizeof(t_query);
	else
	{
		free(q);
		q = NULL;
	}
	fclose(f);
	return (q);
}
