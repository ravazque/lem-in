/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   lem_in.h                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: acerezo- <acerezo-@student.42madrid.com    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/15 20:59:16 by ravazque          #+#    #+#             */
/*   Updated: 2026/09/08 17:49:53 by acerezo-         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef LEM_IN_H
# define LEM_IN_H

# include "../lib/libft.h"
# include <limits.h>

# define HASH_SIZE 1024
# define ROOMS_INIT_CAP 64
# define START_ROOM 1
# define END_ROOM 2
# define INIT_CAP 64
# define READ_BUF 4096
# define LINKS_INIT_CAP 64
# define OUT_BUF 65536
# define INF 2147483647

# define ARGS_ERR \
	"Error!\nCompile the executable without any arguments.\n"

# define ERR \
	"ERROR\n"

typedef struct s_room
{
	char			*name;
	int				x;
	int				y;
	int				id;
}	t_room;

typedef struct s_link
{
	int		from;
	int		to;
}	t_link;

typedef struct s_hash_entry
{
	char				*key;
	t_room				*room;
	struct s_hash_entry	*next;
}	t_hash_entry;

typedef struct s_hash_table
{
	t_hash_entry	**buckets;
	int				size;
}	t_hash_table;

typedef struct s_path
{
	int				*rooms;
	int				len;
	int				ants_assigned;
	int				first_ant;
	struct s_path	*next;
}	t_path;

/* Residual graph: edges paired with their reverse, the Dijkstra scratch state
** and one flow decomposition (route nodes, rooms taken, endpoints). */
typedef struct s_edge
{
	int				to;
	int				cap;
	int				is_rev;
	struct s_edge	*rev;
	struct s_edge	*next;
}	t_edge;

typedef struct s_flow
{
	t_edge	**parent;
	int		*dist;
	int		*pot;
	int		*bhead;
	int		*enode;
	int		*enext;
	char	*done;
	int		ecnt;
	int		nbuck;
	int		src;
	int		sink;
}	t_flow;

typedef struct s_decomp
{
	int		*nodes;
	char	*used;
	t_edge	*cur;
	int		src;
	int		sink;
}	t_decomp;

/* Node-split graph: room id becomes in (id*2) and out (id*2+1). */
typedef struct s_graph
{
	t_room			**rooms;
	t_link			*links;
	int				num_rooms;
	int				rooms_cap;
	int				num_links;
	int				links_cap;
	int				start_id;
	int				end_id;
	t_edge			**adj;
	int				num_nodes;
	int				num_edges;
}	t_graph;

typedef struct s_input
{
	char			**lines;
	int				count;
	int				capacity;
}	t_input;

typedef struct s_buf
{
	char			*data;
	size_t			len;
	size_t			cap;
}	t_buf;

typedef struct s_lem_in
{
	int				num_ants;
	t_graph			graph;
	t_hash_table	*hash;
	t_path			*paths;
	int				num_paths;
	t_input			input;
}	t_lem_in;

// =[ parsing ]============================================================= //

char			*read_stdin(size_t *out_len);
int				parse_input(t_lem_in *lem);
int				parse_room(t_lem_in *lem, char *line, int type);
int				parse_link(t_lem_in *lem, char *line);
int				store_line(t_input *input, char *line);

// =[ graph ]=============================================================== //

void			graph_init(t_lem_in *lem);
void			node_split(t_lem_in *lem);
int				add_edge(t_graph *graph, int from, int to, int cap);
t_hash_table	*hash_new(int size);
void			hash_insert(t_hash_table *ht, char *key, t_room *room);
t_room			*hash_lookup(t_hash_table *ht, char *key);
void			hash_free(t_hash_table *ht);

// =[ solver ]============================================================== //

int				algorithm(t_lem_in *lem);
int				alloc_flow(t_graph *g, t_flow *f);
void			free_flow(t_flow *f);
int				shortest_path(t_graph *g, t_flow *f);
t_path			*extract_paths(t_lem_in *lem);
t_path			*sort_paths(t_path *head);
int				select_paths(t_lem_in *lem);
long			calc_turns(t_path *paths, int num_paths, int num_ants);
void			assign_counts(t_lem_in *lem, t_path **arr, int k);

// =[ simulation ]========================================================== //

void			assign_ants(t_lem_in *lem);
void			simulate(t_lem_in *lem);
int				buf_append(t_buf *b, const char *s, size_t n);
int				buf_flush(t_buf *b);
int				buf_putnbr(t_buf *b, int n);

// =[ utils ]=============================================================== //

void			error_exit(t_lem_in *lem);
void			free_split(char **arr);
void			free_all(t_lem_in *lem);
void			free_paths(t_path *paths);

// ========================================================================= //

#endif
