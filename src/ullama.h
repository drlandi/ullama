/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   ullama.h                                         :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#ifndef ULLAMA_H
# define ULLAMA_H

# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <time.h>
# include <unistd.h>
# include "llama.h"

# define ULL_CTX		4096
# define ULL_THREADS	4
# define ULL_MAX_GEN	1024
# define ULL_MAX_MSG	32
# define ULL_BUF		65536
# define ULL_REPLY		32768

typedef struct s_ull
{
	struct llama_model			*model;
	struct llama_context		*ctx;
	struct llama_sampler		*smpl;
	const struct llama_vocab	*vocab;
	llama_chat_message			msgs[ULL_MAX_MSG];
	int							n_msg;
	int							prev_len;
	char						*buf;
	char						*reply;
}	t_ull;

int		ull_open(t_ull *u, const char *path);
void	ull_close(t_ull *u);
int		ull_turn(t_ull *u, const char *user);
void	chat_clear(t_ull *u);
void	chat_reset(t_ull *u);
int		chat_add(t_ull *u, const char *role, const char *text);
int		chat_render(t_ull *u, int add_ass);
int		chat_fits(t_ull *u, int extra);

#endif
