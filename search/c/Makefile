NAME		= msearch_bench
SRC			= bench.c search.c mapfile.c queries.c stats.c sysinfo.c
OBJ			= $(SRC:.c=.o)
CC			= gcc
CFLAGS		= -Wall -Wextra -Werror -O2

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(OBJ) -o $(NAME)

%.o: %.c msearch.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
