/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::     */
/*   main.c                                           :+:      :+:    :+:     */
/*                                                  +:+ +:+         +:+       */
/*   By: dlandi <dlandi@student.42.fr>            +#+  +:+       +#+          */
/*                                              +#+#+#+#+#+   +#+             */
/*   Created: 2026/09/29 15:50:00 by dlandi          #+#    #+#               */
/*   Updated: 2026/09/29 15:50:00 by dlandi         ###   ########.fr         */
/*                                                                            */
/* ************************************************************************** */

#include "ullama.h"

static void	run_repl(t_ull *u)
{
	char	*line;
	size_t	cap;

	line = NULL;
	cap = 0;
	while (1)
	{
		printf("\n> ");
		fflush(stdout);
		if (getline(&line, &cap, stdin) <= 0)
			break ;
		line[strcspn(line, "\n")] = '\0';
		if (line[0] && ull_turn(u, line))
			fputs("[uLLAMA] error: could not process prompt\n", stderr);
	}
	free(line);
}

static int	run_piped(t_ull *u)
{
	char	*text;
	size_t	cap;
	int		ret;

	text = NULL;
	cap = 0;
	ret = 1;
	if (getdelim(&text, &cap, '\0', stdin) > 0)
		ret = ull_turn(u, text);
	free(text);
	return (ret);
}

int	main(int argc, char **argv)
{
	t_ull	u;
	int		ret;

	if (argc < 2)
	{
		fputs("usage: ullama <model.gguf> [prompt]\n", stderr);
		return (1);
	}
	ret = ull_open(&u, argv[1]);
	if (ret)
		fputs("[uLLAMA] error: could not initialise model\n", stderr);
	else if (argc >= 3)
		ret = ull_turn(&u, argv[2]);
	else if (isatty(STDIN_FILENO))
		run_repl(&u);
	else
		ret = run_piped(&u);
	ull_close(&u);
	return (ret);
}
