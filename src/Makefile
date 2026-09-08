NAME		= ullama
SRC			= ullama.c
OBJ			= $(SRC:.c=.o)
CC			= gcc
CFLAGS		= -Wall -Wextra -Werror -O3
INCLUDES	= -I../../llama.cpp/include -I../../llama.cpp/ggml/include
LIBS		= -L../../llama.cpp/build/bin -lllama -lpthread -lm

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(OBJ) -o $(NAME) $(LIBS)

%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

clean:
	rm -f $(OBJ)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re