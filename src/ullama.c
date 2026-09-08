/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ullama.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dlandi <dlandi@student.42.fr>              +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/09/07 23:05:16 by dlandi            #+#    #+#             */
/*   Updated: 2026/09/07 23:05:18 by dlandi           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "llama.h"
#include "ullama.h"

struct llama_context	*init_engine(const char *path, struct llama_model **m)
{
	struct llama_context_params	cp;

	if (!freopen("/dev/null", "w", stderr))
		return (NULL);
	*m = llama_model_load_from_file(path,
			llama_model_default_params());
	if (!*m)
		return (NULL);
	cp = llama_context_default_params();
	cp.n_ctx = 2048;
	cp.n_threads = 4;
	return (llama_init_from_model(*m, cp));
}

struct llama_sampler	*init_sampler(void)
{
	struct llama_sampler_chain_params	scp;
	struct llama_sampler				*smpl;

	scp = llama_sampler_chain_default_params();
	smpl = llama_sampler_chain_init(scp);
	llama_sampler_chain_add(smpl, llama_sampler_init_top_k(40));
	llama_sampler_chain_add(smpl, llama_sampler_init_top_p(0.9f, 1));
	llama_sampler_chain_add(smpl, llama_sampler_init_temp(0.7f));
	llama_sampler_chain_add(smpl, llama_sampler_init_dist(1234));
	return (smpl);
}

int	print_tok(const struct llama_vocab *v, llama_token t,
			struct llama_context *c)
{
	char	b[256];

	memset(b, 0, 256);
	if (llama_token_to_piece(v, t, b, 255, 0, true) > 0)
	{
		printf("%s", b);
		fflush(stdout);
	}
	return (llama_decode(c, llama_batch_get_one(&t, 1)));
}

void	run_repl(struct llama_context *c, struct llama_sampler *smpl)
{
	char						b[1024];
	llama_token					t[2048];
	const struct llama_vocab	*v;
	int							g;

	v = llama_model_get_vocab(llama_get_model(c));
	while (printf("\n> ") && fgets(b, 1024, stdin))
	{
		if (b[0] == '\n' || llama_decode(c, llama_batch_get_one(t,
			llama_tokenize(v, b, strlen(b), t, 2048, true, true))) != 0)
			continue ;
		printf("\n--- Response ---\n");
		{
			struct timespec	s, e; double sec;
			clock_gettime(CLOCK_MONOTONIC, &s);
			g = 0;
			while (++g < 256 && !llama_vocab_is_eog(v, t[0]))
				if (print_tok(v, (t[0] = llama_sampler_sample(smpl, c, -1)), c) != 0) break ;
			clock_gettime(CLOCK_MONOTONIC, &e);
			sec = (e.tv_sec - s.tv_sec) + (e.tv_nsec - s.tv_nsec) / 1e9;
			if (sec > 0) printf("\n[%.2f tok/s]\n", g / sec);
		}
	}
}

int	main(int argc, char **argv)
{
	struct llama_model		*m;
	struct llama_context	*c;
	struct llama_sampler	*smpl;

	if (argc < 2)
		return (1);
	llama_backend_init();
	m = NULL;
	c = init_engine(argv[1], &m);
	if (c)
	{
		smpl = init_sampler();
		run_repl(c, smpl);
		llama_sampler_free(smpl);
		llama_free(c);
	}
	if (m)
		llama_model_free(m);
	llama_backend_free();
	return (0);
}