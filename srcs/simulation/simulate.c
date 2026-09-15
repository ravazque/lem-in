/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   simulate.c                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: ravazque <ravazque@student.42madrid.com    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/15 20:58:45 by ravazque          #+#    #+#             */
/*   Updated: 2026/09/09 12:10:04 by ravazque         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "lem_in.h"

/* Ant j of a route leaves on turn j+1 and is then at index turn - j. */
void	assign_ants(t_lem_in *lem)
{
	t_path	*p;
	long	base;

	base = 1;
	p = lem->paths;
	while (p)
	{
		p->first_ant = (int)base;
		base += p->ants_assigned;
		p = p->next;
	}
}

static int	emit_token(t_buf *b, int ant_id, char *name, int *first)
{
	if (!*first && !buf_append(b, " ", 1))
		return (0);
	*first = 0;
	if (!buf_append(b, "L", 1) || !buf_putnbr(b, ant_id))
		return (0);
	if (!buf_append(b, "-", 1) || !buf_append(b, name, ft_strlen(name)))
		return (0);
	return (1);
}

static int	emit_turn(t_buf *b, t_lem_in *lem, long t)
{
	t_path	*p;
	char	*name;
	long	j;
	int		first;

	first = 1;
	p = lem->paths;
	while (p)
	{
		j = t - p->len;
		if (j < 0)
			j = 0;
		while (j <= t - 1 && j < p->ants_assigned)
		{
			name = lem->graph.rooms[p->rooms[t - j]]->name;
			if (!emit_token(b, p->first_ant + (int)j, name, &first))
				return (0);
			j++;
		}
		p = p->next;
	}
	return (buf_append(b, "\n", 1));
}

static int	echo_input(t_buf *b, t_lem_in *lem)
{
	char	*line;
	int		i;

	i = 0;
	while (i < lem->input.count)
	{
		line = lem->input.lines[i];
		if (!buf_append(b, line, ft_strlen(line)))
			return (0);
		if (!buf_append(b, "\n", 1))
			return (0);
		i++;
	}
	return (buf_append(b, "\n", 1));
}

void	simulate(t_lem_in *lem)
{
	t_buf	b;
	t_path	*p;
	long	turns;
	long	t;

	ft_memset(&b, 0, sizeof(t_buf));
	turns = 0;
	p = lem->paths;
	while (p)
	{
		if (p->ants_assigned > 0
			&& (long)p->ants_assigned + p->len - 1 > turns)
			turns = (long)p->ants_assigned + p->len - 1;
		p = p->next;
	}
	t = 0;
	if (!echo_input(&b, lem))
		return (free(b.data), error_exit(lem));
	while (++t <= turns)
		if (!emit_turn(&b, lem, t))
			return (free(b.data), error_exit(lem));
	if (!buf_flush(&b))
		return (free(b.data), error_exit(lem));
	free(b.data);
}
