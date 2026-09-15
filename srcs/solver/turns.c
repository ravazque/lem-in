/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   turns.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: ravazque <ravazque@student.42madrid.com    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/15 20:58:42 by ravazque          #+#    #+#             */
/*   Updated: 2026/09/09 12:10:04 by ravazque         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "lem_in.h"

static long	capacity(t_path *paths, int num_paths, long t)
{
	long	sum;
	int		i;

	sum = 0;
	i = 0;
	while (i < num_paths && paths)
	{
		if (t >= paths->len)
			sum += t - paths->len + 1;
		paths = paths->next;
		i++;
	}
	return (sum);
}

static long	min_len(t_path *paths, int num_paths)
{
	long	best;
	int		i;

	best = INF;
	i = 0;
	while (i < num_paths && paths)
	{
		if (paths->len < best)
			best = paths->len;
		paths = paths->next;
		i++;
	}
	return (best);
}

/* Fewest turns for num_ants: binary search on the ants delivered by turn t. */
long	calc_turns(t_path *paths, int num_paths, int num_ants)
{
	long	lo;
	long	hi;
	long	mid;

	lo = min_len(paths, num_paths);
	hi = lo + num_ants;
	while (lo < hi)
	{
		mid = lo + (hi - lo) / 2;
		if (capacity(paths, num_paths, mid) >= num_ants)
			hi = mid;
		else
			lo = mid + 1;
	}
	return (lo);
}

static long	fill_counts(t_path **arr, int k, long turns, int num_ants)
{
	long	total;
	int		i;

	total = 0;
	i = 0;
	while (i < k)
	{
		arr[i]->ants_assigned = 0;
		if (turns >= arr[i]->len)
			arr[i]->ants_assigned = (int)(turns - arr[i]->len + 1);
		total += arr[i]->ants_assigned;
		i++;
	}
	return (total - num_ants);
}

/* Fills every route to the turn limit and drops the surplus from the longest
** ones, which is the split a one-ant-at-a-time greedy would reach. */
void	assign_counts(t_lem_in *lem, t_path **arr, int k)
{
	long	extra;
	int		i;

	extra = fill_counts(arr, k, calc_turns(lem->paths, k, lem->num_ants),
			lem->num_ants);
	i = k - 1;
	while (extra > 0 && i >= 0)
	{
		if (arr[i]->ants_assigned < extra)
		{
			extra -= arr[i]->ants_assigned;
			arr[i]->ants_assigned = 0;
		}
		else
		{
			arr[i]->ants_assigned -= (int)extra;
			extra = 0;
		}
		i--;
	}
}
