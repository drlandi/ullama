/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   gen.c                                            :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include "ullama.h"

static double	now_s(void)
{
	struct timespec	ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (ts.tv_sec + ts.tv_nsec / 1e9);
}

static int	feed_text(t_ull *u, const char *text, int first)
{
	llama_token	*tok;
	int			n;
	int			off;
	int			step;

	tok = malloc((strlen(text) + 8) * sizeof(llama_token));
	if (!tok)
		return (1);
	n = llama_tokenize(u->vocab, text, (int)strlen(text), tok,
			(int)strlen(text) + 8, first, true);
	off = 0;
	while (n >= 0 && off < n)
	{
		step = n - off;
		if (step > 512)
			step = 512;
		if (llama_decode(u->ctx, llama_batch_get_one(tok + off, step)))
			n = -1;
		off += step;
	}
	free(tok);
	return (n < 0);
}

static int	emit(t_ull *u, llama_token tok, int *len)
{
	char	piece[256];
	int		n;

	n = llama_token_to_piece(u->vocab, tok, piece, sizeof(piece), 0, false);
	if (n < 0 || *len + n >= ULL_REPLY)
		return (1);
	fwrite(piece, 1, n, stdout);
	fflush(stdout);
	memcpy(u->reply + *len, piece, n);
	*len += n;
	u->reply[*len] = '\0';
	return (0);
}

static int	generate(t_ull *u)
{
	llama_token	tok;
	int			len;
	int			count;

	len = 0;
	count = 0;
	u->reply[0] = '\0';
	while (count < ULL_MAX_GEN)
	{
		tok = llama_sampler_sample(u->smpl, u->ctx, -1);
		if (llama_vocab_is_eog(u->vocab, tok) || emit(u, tok, &len))
			break ;
		if (llama_decode(u->ctx, llama_batch_get_one(&tok, 1)))
			break ;
		count++;
	}
	return (count);
}

int	ull_turn(t_ull *u, const char *user)
{
	int		plen;
	int		gen;
	double	t0;

	if (!chat_fits(u, (int)strlen(user) + 512))
		chat_reset(u);
	plen = -1;
	if (!chat_add(u, "user", user))
		plen = chat_render(u, 1);
	if (plen < 0 || feed_text(u, u->buf + u->prev_len, !u->prev_len))
	{
		chat_reset(u);
		return (1);
	}
	t0 = now_s();
	gen = generate(u);
	printf("\n");
	fprintf(stderr, "[%d tok, %.2f tok/s]\n", gen, gen / (now_s() - t0));
	if (chat_add(u, "assistant", u->reply))
		chat_reset(u);
	else
		u->prev_len = plen + (int)strlen(u->reply);
	return (0);
}
