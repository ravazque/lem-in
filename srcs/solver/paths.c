/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   paths.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: ravazque <ravazque@student.42madrid.com    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/15 20:58:40 by ravazque          #+#    #+#             */
/*   Updated: 2026/09/09 12:10:04 by ravazque         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "lem_in.h"

static t_edge	*find_flow_edge(t_graph *g, int node, t_decomp *d)
{
	t_edge	*e;

	e = g->adj[node];
	while (e)
	{
		if (e->is_rev == 0 && e->cap == 0
			&& (e->to == d->sink || !d->used[e->to]))
			return (e);
		e = e->next;
	}
	return (NULL);
}

/* Follows saturated forward edges from d->cur to the sink, marking rooms. */
static int	walk_flow(t_graph *g, t_decomp *d)
{
	t_edge	*e;
	int		cur;
	int		n;

	n = 0;
	d->nodes[n++] = d->src;
	cur = d->cur->to;
	d->nodes[n++] = cur;
	while (cur != d->sink)
	{
		if (d->used[cur])
			return (0);
		d->used[cur] = 1;
		e = find_flow_edge(g, cur, d);
		if (!e)
			return (0);
		cur = e->to;
		d->nodes[n++] = cur;
	}
	return (n);
}

static t_path	*build_path(int *nodes, int n)
{
	t_path	*path;
	int		i;
	int		count;

	path = ft_calloc(1, sizeof(t_path));
	if (!path)
		return (NULL);
	path->rooms = malloc(sizeof(int) * n);
	if (!path->rooms)
		return (free(path), NULL);
	count = 0;
	i = 0;
	while (i < n)
	{
		if (count == 0 || path->rooms[count - 1] != nodes[i] / 2)
			path->rooms[count++] = nodes[i] / 2;
		i++;
	}
	path->len = count - 1;
	return (path);
}

static t_path	*collect(t_lem_in *lem, t_decomp *d)
{
	t_path	*head;
	t_path	*path;
	int		n;

	head = NULL;
	while (d->cur)
	{
		n = 0;
		if (d->cur->is_rev == 0 && d->cur->cap == 0)
			n = walk_flow(&lem->graph, d);
		d->cur = d->cur->next;
		if (n > 0)
		{
			path = build_path(d->nodes, n);
			if (!path)
				return (free_paths(head), NULL);
			path->next = head;
			head = path;
		}
	}
	return (head);
}

/* Reads the routes out of the flow without consuming it, one per src edge. */
t_path	*extract_paths(t_lem_in *lem)
{
	t_decomp	d;
	t_path		*head;

	d.src = lem->graph.start_id * 2 + 1;
	d.sink = lem->graph.end_id * 2;
	d.cur = lem->graph.adj[d.src];
	d.nodes = malloc(sizeof(int) * (lem->graph.num_nodes + 2));
	d.used = ft_calloc(lem->graph.num_nodes, 1);
	if (!d.nodes || !d.used)
		return (free(d.nodes), free(d.used), error_exit(lem), NULL);
	d.used[d.src] = 1;
	head = collect(lem, &d);
	free(d.nodes);
	free(d.used);
	if (!head)
		error_exit(lem);
	return (head);
}
