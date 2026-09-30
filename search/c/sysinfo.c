/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   sysinfo.c                                        :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include <fcntl.h>
#include <sys/resource.h>
#include <unistd.h>
#include "msearch.h"

void	drop_cache(const char *path)
{
	int	fd;

	fd = open(path, O_RDONLY);
	if (fd < 0)
		return ;
	posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
	close(fd);
}

void	read_faults(long *minor, long *major)
{
	struct rusage	ru;

	getrusage(RUSAGE_SELF, &ru);
	*minor = ru.ru_minflt;
	*major = ru.ru_majflt;
}
