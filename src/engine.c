/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   engine.c                                         :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include "ullama.h"

static void	quiet_log(enum ggml_log_level level, const char *text, void *ud)
{
	(void)ud;
	if (level == GGML_LOG_LEVEL_ERROR)
		fputs(text, stderr);
}

static struct llama_sampler	*make_sampler(void)
{
	struct llama_sampler	*s;

	s = llama_sampler_chain_init(llama_sampler_chain_default_params());
	llama_sampler_chain_add(s, llama_sampler_init_top_k(40));
	llama_sampler_chain_add(s, llama_sampler_init_top_p(0.9f, 1));
	llama_sampler_chain_add(s, llama_sampler_init_temp(0.7f));
	llama_sampler_chain_add(s, llama_sampler_init_dist(LLAMA_DEFAULT_SEED));
	return (s);
}

int	ull_open(t_ull *u, const char *path)
{
	struct llama_context_params	cp;

	memset(u, 0, sizeof(*u));
	llama_log_set(quiet_log, NULL);
	llama_backend_init();
	u->model = llama_model_load_from_file(path,
			llama_model_default_params());
	if (!u->model)
		return (1);
	u->vocab = llama_model_get_vocab(u->model);
	cp = llama_context_default_params();
	cp.n_ctx = ULL_CTX;
	cp.n_threads = ULL_THREADS;
	cp.n_threads_batch = ULL_THREADS;
	u->ctx = llama_init_from_model(u->model, cp);
	u->smpl = make_sampler();
	u->buf = malloc(ULL_BUF);
	u->reply = malloc(ULL_REPLY);
	if (!u->ctx || !u->buf || !u->reply)
		return (1);
	return (0);
}

void	ull_close(t_ull *u)
{
	chat_clear(u);
	free(u->buf);
	free(u->reply);
	if (u->smpl)
		llama_sampler_free(u->smpl);
	if (u->ctx)
		llama_free(u->ctx);
	if (u->model)
		llama_model_free(u->model);
	llama_backend_free();
}
