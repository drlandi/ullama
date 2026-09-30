/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   chat.c                                           :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include "ullama.h"

void	chat_clear(t_ull *u)
{
	while (u->n_msg > 0)
	{
		u->n_msg--;
		free((void *)u->msgs[u->n_msg].content);
	}
	u->prev_len = 0;
}

void	chat_reset(t_ull *u)
{
	chat_clear(u);
	llama_memory_clear(llama_get_memory(u->ctx), true);
}

int	chat_add(t_ull *u, const char *role, const char *text)
{
	char	*copy;

	if (u->n_msg >= ULL_MAX_MSG)
		return (1);
	copy = strdup(text);
	if (!copy)
		return (1);
	u->msgs[u->n_msg].role = role;
	u->msgs[u->n_msg].content = copy;
	u->n_msg++;
	return (0);
}

int	chat_render(t_ull *u, int add_ass)
{
	const char	*tmpl;
	int			len;

	tmpl = llama_model_chat_template(u->model, NULL);
	len = llama_chat_apply_template(tmpl, u->msgs, u->n_msg, add_ass,
			u->buf, ULL_BUF - 1);
	if (len < 0 || len >= ULL_BUF - 1)
		return (-1);
	u->buf[len] = '\0';
	return (len);
}

int	chat_fits(t_ull *u, int extra)
{
	int	used;

	used = llama_memory_seq_pos_max(llama_get_memory(u->ctx), 0) + 1;
	if (u->n_msg + 2 > ULL_MAX_MSG)
		return (0);
	return (used + extra + ULL_MAX_GEN < (int)llama_n_ctx(u->ctx));
}
