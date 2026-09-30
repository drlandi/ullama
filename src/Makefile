NAME		= ullama
SRC			= main.c engine.c chat.c gen.c
OBJ			= $(SRC:.c=.o)
CC			= gcc
CFLAGS		= -Wall -Wextra -Werror -O3
LLAMA_DIR	?= $(HOME)/tools/llama.cpp
INCLUDES	= -I$(LLAMA_DIR)/include -I$(LLAMA_DIR)/ggml/include
LIBDIR		= $(LLAMA_DIR)/build/bin
GGML		= $(patsubst $(LIBDIR)/lib%.so,-l%,$(wildcard $(LIBDIR)/libggml*.so))
LIBS		= -L$(LIBDIR) -Wl,--disable-new-dtags,-rpath,$(LIBDIR) \
			  -Wl,--no-as-needed -lllama $(GGML) -lpthread -lm

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(OBJ) -o $(NAME) $(LIBS)

%.o: %.c ullama.h
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

clean:
	rm -f $(OBJ)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
