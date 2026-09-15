/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   algorithm.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: ravazque <ravazque@student.42madrid.com    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/15 20:58:42 by ravazque          #+#    #+#             */
/*   Updated: 2026/09/09 12:10:04 by ravazque         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "lem_in.h"

static void	augment(t_flow *f)
{
	t_edge	*e;
	int		node;

	node = f->sink;
	while (node != f->src)
	{
		e = f->parent[node];
		e->cap -= 1;
		e->rev->cap += 1;
		node = e->rev->to;
	}
}

/* A flow value that cannot beat the best turn count is never decomposed. */
static int	worth_trying(t_lem_in *lem, int flow, long best, long lmin)
{
	long	bound;

	if (best < 0)
		return (1);
	bound = ((long)lem->num_ants + flow - 1) / flow + lmin - 1;
	return (bound < best);
}

static void	keep_best(t_lem_in *lem, int flow, long *best)
{
	t_path	*paths;
	long	turns;

	paths = extract_paths(lem);
	if (!paths)
		return ;
	turns = calc_turns(paths, flow, lem->num_ants);
	if (*best >= 0 && turns >= *best)
		return (free_paths(paths));
	*best = turns;
	free_paths(lem->paths);
	lem->paths = paths;
	lem->num_paths = flow;
}

/* Min-cost max-flow out(start) -> in(end): each pass adds one room-disjoint
** route; the flow value finishing in the fewest turns stays in lem->paths. */
int	algorithm(t_lem_in *lem)
{
	t_flow	f;
	int		flow;
	long	best;
	long	lmin;

	if (!alloc_flow(&lem->graph, &f))
		return (0);
	flow = 0;
	best = -1;
	lmin = 0;
	while (best != lmin && shortest_path(&lem->graph, &f))
	{
		augment(&f);
		flow++;
		if (worth_trying(lem, flow, best, lmin))
			keep_best(lem, flow, &best);
		if (flow == 1 && lem->paths)
			lmin = lem->paths->len;
	}
	free_flow(&f);
	return (lem->num_paths);
}
